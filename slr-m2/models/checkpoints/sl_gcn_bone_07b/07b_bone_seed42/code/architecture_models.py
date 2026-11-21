"""PyTorch adaptations of the pinned SPOTER, SL-GCN and VSNet papers."""
import math

import torch
from torch import nn
from torch.nn import functional as F

from architecture_data import CHANNELS, FRAMES, NODE_COUNTS, SL_EDGES, VS_EDGES


def mask_frames(x, real):
    return x.masked_fill(~real[:, None, :, None], 0.)


def mean_frames(x, real):
    return mask_frames(x, real).sum(dim=2) / real.sum(dim=1).clamp_min(1)[:, None, None]


class ClassQueryLayer(nn.Module):
    def __init__(self, width):
        super().__init__()
        self.cross = nn.MultiheadAttention(width, 9, dropout=.1, batch_first=True)
        self.ffn = nn.Sequential(nn.Linear(width, 2048), nn.ReLU(), nn.Dropout(.1),
                                 nn.Linear(2048, width))
        self.norms = nn.ModuleList(nn.LayerNorm(width) for _ in range(3))
        self.dropout = nn.Dropout(.1)

    def forward(self, query, memory, padding):
        query = self.norms[0](query + self.dropout(query))
        attended, _ = self.cross(query, memory, memory, key_padding_mask=padding,
                                 need_weights=False)
        query = self.norms[1](query + self.dropout(attended))
        return self.norms[2](query + self.dropout(self.ffn(query)))


class Spoter(nn.Module):
    def __init__(self, classes):
        super().__init__()
        width = 108
        self.input = nn.Linear(NODE_COUNTS['spoter'] * len(CHANNELS), width)
        self.temporal_positions = nn.Parameter(torch.empty(1, FRAMES, width))
        self.class_query = nn.Parameter(torch.empty(1, 1, width))
        encoder = nn.TransformerEncoderLayer(width, 9, 2048, dropout=.1, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder, 6, nn.LayerNorm(width),
                                             enable_nested_tensor=False)
        self.decoder = nn.ModuleList(ClassQueryLayer(width) for _ in range(6))
        self.decoder_norm = nn.LayerNorm(width)
        self.classifier = nn.Linear(width, classes)
        for parameter in self.parameters():
            if parameter.ndim > 1:
                nn.init.xavier_uniform_(parameter)
        nn.init.normal_(self.temporal_positions, std=.02)
        nn.init.normal_(self.class_query, std=.02)

    def forward(self, x, real, time):
        tokens = self.input(x.masked_fill(~real[..., None, None], 0.).flatten(2))
        tokens = tokens + self.temporal_positions[:, :tokens.size(1)]
        memory = self.encoder(tokens, src_key_padding_mask=~real)
        query = self.class_query.expand(x.shape[0], -1, -1)
        for layer in self.decoder:
            query = layer(query, memory, ~real)
        return self.classifier(self.decoder_norm(query[:, 0]))


def spatial_adjacency(nodes, edges):
    inward = torch.zeros(nodes, nodes)
    for parent, child in edges:
        inward[child, parent] = 1.
    outward = inward.T
    return torch.stack((torch.eye(nodes), inward / inward.sum(0).clamp_min(1),
                        outward / outward.sum(0).clamp_min(1)))


def conv_bn(channels_in, channels_out, kernel, stride=1):
    conv = nn.Conv2d(channels_in, channels_out, (kernel, 1),
                     stride=(stride, 1), padding=(kernel // 2, 0))
    nn.init.kaiming_normal_(conv.weight, mode='fan_out')
    nn.init.zeros_(conv.bias)
    return nn.Sequential(conv, nn.BatchNorm2d(channels_out))


class DecoupledGraph(nn.Module):
    def __init__(self, channels_in, channels_out, adjacency, groups):
        super().__init__()
        self.groups = groups
        self.adjacency = nn.Parameter(adjacency[:, None].repeat(1, groups, 1, 1))
        self.project = conv_bn(channels_in, 3 * channels_out, 1)
        nn.init.normal_(self.project[0].weight, std=math.sqrt(.5 / (3 * channels_out)))
        nn.init.constant_(self.project[0].bias, 1e-6)
        self.norm = nn.BatchNorm2d(channels_out)
        nn.init.constant_(self.norm.weight, 1e-6)
        self.skip = (nn.Identity() if channels_in == channels_out
                     else conv_bn(channels_in, channels_out, 1))

    def forward(self, x):
        # Retain signed edges without amplifying nearly empty adjacency columns.
        degree = self.adjacency.abs().sum(dim=-2, keepdim=True).clamp_min(1.)
        adjacency = self.adjacency / degree
        n, _, frames, nodes = x.shape
        projected = self.project(x).reshape(n, 3, -1, self.groups, frames, nodes)
        y = torch.einsum('nkrgtv,kgvw->nrgtw', projected, adjacency)
        return F.relu(self.norm(y.flatten(1, 2)) + self.skip(x))


class STCAttention(nn.Module):
    def __init__(self, channels, nodes):
        super().__init__()
        kernel = nodes if nodes % 2 else nodes - 1
        self.spatial = nn.Conv1d(channels, 1, kernel, padding=kernel // 2)
        self.temporal = nn.Conv1d(channels, 1, 9, padding=4)
        self.channel = nn.Sequential(nn.Linear(channels, channels // 2), nn.ReLU(),
                                     nn.Linear(channels // 2, channels))
        nn.init.xavier_normal_(self.spatial.weight)
        nn.init.zeros_(self.spatial.bias)
        nn.init.zeros_(self.temporal.weight)
        nn.init.zeros_(self.temporal.bias)
        nn.init.zeros_(self.channel[-1].weight)
        nn.init.zeros_(self.channel[-1].bias)

    def forward(self, x, real):
        x = x * (1 + self.spatial(mean_frames(x, real)).sigmoid().unsqueeze(2))
        x = x * (1 + self.temporal(x.mean(-1)).sigmoid().unsqueeze(-1))
        channel = self.channel(mean_frames(x, real).mean(-1))
        return x * (1 + channel.sigmoid()[:, :, None, None])


def activation_seeds(energy, eligible, gamma):
    eligible = eligible.expand_as(energy)
    energy = energy.masked_fill(~eligible, 0.)
    probability = (energy * eligible.sum() * gamma / energy.sum().clamp_min(1e-8))
    return torch.bernoulli(probability.clamp_max(1.))


class DropGraph(nn.Module):
    def __init__(self, adjacency, block_size=41):
        super().__init__()
        self.block_size = block_size
        self.register_buffer('neighbors', adjacency.sum(0))

    def forward(self, x, real, keep, temporal_size=None):
        if not self.training or keep == 1.:
            return x
        spatial_energy = mean_frames(x.detach().abs(), real).mean(1)
        spatial_seeds = activation_seeds(spatial_energy, real.any(1, keepdim=True),
                                         (1 - keep) / 2.92)
        spatial_keep = (spatial_seeds @ self.neighbors) <= .001
        x = x * spatial_keep[:, None, None, :] * (
            spatial_keep.numel() / spatial_keep.sum().clamp_min(1))
        size = temporal_size or self.block_size
        temporal_energy = x.detach().abs().mean((1, 3))
        temporal_seeds = activation_seeds(temporal_energy, real, (1 - keep) / size)
        dropped = F.max_pool1d(temporal_seeds[:, None], size, stride=1, padding=size // 2)
        temporal_keep = (dropped[:, 0] == 0) & real
        return x * temporal_keep[:, None, :, None] * (
            real.sum() / temporal_keep.sum().clamp_min(1))


class GraphTemporalBlock(nn.Module):
    def __init__(self, channels_in, channels_out, adjacency, groups, stride=1,
                 residual=True):
        super().__init__()
        self.stride = stride
        self.graph = DecoupledGraph(channels_in, channels_out, adjacency, groups)
        self.attention = STCAttention(channels_out, adjacency.shape[-1])
        self.temporal = conv_bn(channels_out, channels_out, 9, stride)
        self.skip = None
        if residual:
            self.skip = (nn.Identity() if stride == 1 and channels_in == channels_out
                         else conv_bn(channels_in, channels_out, 1, stride))
        self.drop = DropGraph(adjacency)

    def forward(self, x, real, keep):
        y = self.attention(mask_frames(self.graph(x), real), real)
        next_real = real[:, ::self.stride]
        y = self.temporal(mask_frames(y, real))
        y = self.drop(mask_frames(y, next_real), next_real, keep, temporal_size=7)
        if self.skip is not None:
            skip = mask_frames(self.skip(x), next_real)
            y = y + self.drop(skip, next_real, keep)
        return mask_frames(F.relu(y), next_real), next_real


class SLGCN(nn.Module):
    def __init__(self, classes):
        super().__init__()
        nodes, channels = NODE_COUNTS['sl_gcn'], len(CHANNELS)
        adjacency = spatial_adjacency(nodes, SL_EDGES)
        self.input_norm = nn.BatchNorm1d(nodes * channels)
        widths = (channels, 64, 64, 64, 64, 128, 128, 128, 256, 256, 256)
        self.blocks = nn.ModuleList(
            GraphTemporalBlock(widths[i], widths[i + 1], adjacency, groups=16,
                               stride=2 if i in (4, 7) else 1, residual=i != 0)
            for i in range(10))
        self.classifier = nn.Linear(256, classes)
        nn.init.normal_(self.classifier.weight, std=math.sqrt(2. / classes))

    def forward(self, x, real, time):
        n, frames, nodes, channels = x.shape
        x = x.masked_fill(~real[..., None, None], 0.)
        x = self.input_norm(x.flatten(2).transpose(1, 2))
        x = mask_frames(x.reshape(n, nodes, channels, frames).permute(0, 2, 3, 1), real)
        for i, block in enumerate(self.blocks):
            x, real = block(x, real, 1. if i < 6 else .9)
        return self.classifier(mean_frames(x, real).mean(-1))


def keep_joint_slots(adjacency, sizes, drops):
    # Score the learned adjacency once per forward, shared across clips as upstream.
    correlation = adjacency.detach().amax(dim=1).sum(dim=(0, 2))
    groups = correlation.split(sizes)
    kept = []
    offset = 0
    for scores, drop in zip(groups, drops):
        order = scores.argsort(stable=True)
        kept.append(order[drop:].sort().values + offset)
        offset += len(scores)
    return torch.cat(kept)


class WindowAttention(nn.Module):
    def __init__(self, channels, interleaved):
        super().__init__()
        self.interleaved = interleaved
        self.heads = 8
        self.pair_qkv = nn.Linear(channels, 3 * channels)
        self.pair_project = nn.Linear(channels, 3 * channels)
        self.relative_bias = nn.Parameter(torch.empty(15, self.heads))
        positions = torch.arange(8).repeat_interleave(4)
        self.register_buffer('relative_index', positions[:, None] - positions[None, :] + 7)
        nn.init.trunc_normal_(self.relative_bias, std=.02)

    def forward(self, x, real):
        n, t, v, c = x.shape
        # Three pairings: both arms, both left-hand groups, both right-hand groups.
        qkv = self.pair_qkv(x).reshape(n, t, 3, 8, 3, 4, c // 4)
        q, k, value = qkv.permute(4, 0, 1, 2, 5, 3, 6).unbind(0)
        paired = F.scaled_dot_product_attention(q, k, value, scale=4 ** -.5)
        paired = paired.transpose(-2, -3).reshape(n, t, v, c)
        paired = self.pair_project(paired)
        if self.interleaved:
            windows = paired.reshape(n, 8, t // 8, v // 4, 4, 3 * c)
            windows = windows.permute(0, 2, 3, 1, 4, 5)
            keys = real.reshape(n, 8, t // 8).transpose(1, 2)
        else:
            windows = paired.reshape(n, t // 8, 8, v // 4, 4, 3 * c)
            windows = windows.permute(0, 1, 3, 2, 4, 5)
            keys = real.reshape(n, t // 8, 8)
        qkv = windows.reshape(n, t // 8, v // 4, 32, 3, self.heads, c // self.heads)
        q, k, value = qkv.permute(4, 0, 1, 2, 5, 3, 6).unbind(0)
        keys = keys.repeat_interleave(4, dim=-1)
        safe_keys = keys | (~keys.any(-1, keepdim=True) & (torch.arange(32, device=x.device) == 0))
        bias = self.relative_bias[self.relative_index].permute(2, 0, 1)
        bias = bias.masked_fill(~safe_keys[:, :, None, None, None, :], float('-inf'))
        attended = F.scaled_dot_product_attention(q, k, value, attn_mask=bias,
                                                  scale=self.heads ** -.5)
        attended = attended.transpose(-3, -2).reshape(n, t // 8, v // 4, 8, 4, c)
        attended = (attended.permute(0, 3, 1, 2, 4, 5) if self.interleaved
                    else attended.permute(0, 1, 3, 2, 4, 5))
        return attended.reshape(n, t, v, c).masked_fill(~real[..., None, None], 0.)


def stochastic_depth(x, probability, training):
    if not training or not probability:
        return x
    keep = 1 - probability
    sample_mask = torch.rand((len(x), 1, 1, 1), device=x.device) < keep
    return x * sample_mask / keep


class VSFormerBlock(nn.Module):
    def __init__(self, channels_in, channels, downsample, drop_path):
        super().__init__()
        self.downsample = conv_bn(channels_in, channels, 7, stride=2) if downsample else None
        self.drop_path = drop_path
        self.norm = nn.LayerNorm(channels)
        self.mapping = nn.Linear(channels, channels)
        self.graph = nn.Parameter(torch.empty(8, 24, 24))
        nn.init.trunc_normal_(self.graph, std=.02)
        width = channels // 4
        self.temporal = nn.Conv2d(width, width, (7, 1), padding=(3, 0), groups=8)
        self.short = WindowAttention(width, interleaved=False)
        self.long = WindowAttention(width, interleaved=True)
        self.project = nn.Linear(channels, channels)
        self.ffn = nn.Sequential(nn.LayerNorm(channels), nn.Linear(channels, 4 * channels),
                                 nn.GELU(), nn.Linear(4 * channels, channels))

    def forward(self, x, real):
        if self.downsample is not None:
            x = self.downsample(mask_frames(x, real))
            real = real[:, ::2]
        x = mask_frames(x, real).permute(0, 2, 3, 1)
        mapped = self.mapping(self.norm(x)).masked_fill(~real[..., None, None], 0.)
        graph, temporal, short, long = mapped.chunk(4, dim=-1)
        grouped = graph.reshape(*graph.shape[:3], 8, -1)
        graph = torch.einsum('btuhd,hvu->btvhd', grouped, self.graph).flatten(-2)
        temporal = self.temporal(temporal.permute(0, 3, 1, 2)).permute(0, 2, 3, 1)
        y = self.project(torch.cat((graph, temporal, self.short(short, real),
                                    self.long(long, real)), dim=-1))
        x = x + stochastic_depth(y, self.drop_path, self.training)
        x = x + stochastic_depth(self.ffn(x), self.drop_path, self.training)
        return mask_frames(x.permute(0, 3, 1, 2), real), real


class VSNet(nn.Module):
    def __init__(self, classes):
        super().__init__()
        nodes = (44, 36, 24)
        widths = (len(CHANNELS), 64, 96, 96)
        self.spd = nn.ModuleList(
            GraphTemporalBlock(widths[i], widths[i + 1], spatial_adjacency(v, edges),
                               groups=8, residual=i != 0)
            for i, (v, edges) in enumerate(zip(nodes, VS_EDGES)))
        self.position_gain = nn.Parameter(torch.empty(96, 24))
        nn.init.trunc_normal_(self.position_gain, std=.02)
        self.register_buffer('frequency', torch.exp(torch.arange(0, 96, 2) * (-math.log(10000.) / 96)))
        widths = (96, 96, 96, 192, 192, 192, 192, 192, 192)
        self.blocks = nn.ModuleList(
            VSFormerBlock(widths[i], widths[i + 1], downsample=i in (2, 4, 6),
                          drop_path=.2 * i / 7)
            for i in range(8))
        self.classifier = nn.Linear(192, classes)

    def forward(self, x, real, time):
        x = mask_frames(x.permute(0, 3, 1, 2), real)
        x, real = self.spd[0](x, real, 1.)
        slots = keep_joint_slots(self.spd[0].graph.adjacency, (6, 6, 8, 8, 8, 8),
                                 (0, 0, 2, 2, 2, 2))
        x, real = self.spd[1](x.index_select(-1, slots), real, .9)
        slots = keep_joint_slots(self.spd[1].graph.adjacency, (6,) * 6, (2,) * 6)
        x, real = self.spd[2](x.index_select(-1, slots), real, .9)
        normalized_time = (2 * time[..., 1] - 1).masked_fill(~real, 0.)
        phase = normalized_time.unsqueeze(-1) * self.frequency
        encoding = torch.stack((phase.sin(), phase.cos()), dim=-1).flatten(2)
        x = mask_frames(x + encoding.transpose(1, 2).unsqueeze(-1)
                        * self.position_gain[:, None, :], real)
        for block in self.blocks:
            x, real = block(x, real)
        return self.classifier(mean_frames(x, real).mean(-1))


def build_model(name, classes=400):
    return {'spoter': Spoter, 'sl_gcn': SLGCN, 'vsnet': VSNet}[name](classes)
