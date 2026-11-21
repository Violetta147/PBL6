"""Timestamp-driven causal arms-down segmentation."""
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class Config:
    onset: float = .35
    leading: float = .3
    rest: float = .35
    trailing: float = .2
    utterance_rest: float = 1.5
    max_duration: float = 15.
    gap: float = .5
    visibility: float = .5
    wrist_below_hip: float = -.15
    elbow_below_shoulder: float = .3

    def __post_init__(self):
        if any(not math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('Configuration must be finite')
        if min(self.onset, self.rest, self.max_duration, self.gap) <= 0:
            raise ValueError('Durations must be positive')
        if min(self.leading, self.trailing) < 0 or self.utterance_rest <= self.rest:
            raise ValueError('Invalid context or utterance duration')


def arm_states(pose, visibility, config):
    states = []
    for shoulder, elbow, wrist, hip in ((0,2,4,6), (1,3,5,7)):
        indices = (shoulder, elbow, wrist, hip)
        if any(visibility[i] < config.visibility or not math.isfinite(float(visibility[i]))
               or not all(math.isfinite(float(v)) for v in pose[i][:2]) for i in indices):
            states.append(None)
            continue
        torso = pose[hip][1] - pose[shoulder][1]
        if torso <= .02:
            states.append(None)
            continue
        down = (pose[wrist][1] >= pose[hip][1] + config.wrist_below_hip * torso
                and pose[elbow][1] >= pose[shoulder][1] + config.elbow_below_shoulder * torso)
        states.append('rest' if down else 'active')
    return states


class Segmenter:
    def __init__(self, config=None):
        self.config = config or Config()
        self.state = 'UNKNOWN'
        self.last = None
        self.rest_since = self.onset_since = self.start = self.unknown_since = None
        self.segment_id = 0
        self.utterance_id = 0
        self.has_segments = False

    def close(self, timestamp, status, reason=None):
        self.segment_id += 1
        result = dict(segment_id=str(self.segment_id), utterance_id=str(self.utterance_id),
                      start=max(0., self.start-self.config.leading), movement_start=self.start,
                      movement_end=self.rest_since if status == 'complete' else timestamp,
                      end=min(timestamp, self.rest_since+self.config.trailing) if status == 'complete' else timestamp,
                      finalized_at=timestamp, status=status, reason=reason)
        self.start = self.onset_since = None
        self.has_segments |= status == 'complete'
        return result

    def feed(self, timestamp, arms):
        if not math.isfinite(timestamp) or timestamp < 0 or (self.last is not None and timestamp <= self.last):
            raise ValueError('Timestamps must be finite and strictly increasing')
        events = []
        gap = self.last is not None and timestamp-self.last > self.config.gap
        self.last = timestamp
        if gap:
            if self.start is not None:
                events.append(self.close(timestamp, 'incomplete', 'timestamp_gap'))
            self.state = 'UNKNOWN'
            self.rest_since = self.onset_since = None
        if None in arms:
            if self.unknown_since is None:
                self.unknown_since = timestamp
            self.rest_since = self.onset_since = None
            if self.start is not None and timestamp-self.unknown_since >= self.config.gap:
                events.append(self.close(timestamp, 'incomplete', 'tracking_loss'))
            self.state = 'UNKNOWN'
            return events
        self.unknown_since = None
        resting = all(arm == 'rest' for arm in arms)
        if self.start is not None and timestamp-self.start >= self.config.max_duration:
            events.append(self.close(timestamp, 'incomplete', 'duration_limit'))
            self.state = 'UNKNOWN'
            self.rest_since = None
        if resting:
            if self.rest_since is None:
                self.rest_since = timestamp
            elapsed = timestamp-self.rest_since
            if self.start is not None:
                self.state = 'END_PENDING'
                if elapsed + 1e-9 >= max(self.config.rest, self.config.trailing):
                    events.append(self.close(timestamp, 'complete'))
                    self.state = 'READY'
            elif elapsed + 1e-9 >= self.config.rest:
                self.state = 'READY'
            self.onset_since = None
            if self.has_segments and elapsed >= self.config.utterance_rest:
                events.append(dict(type='utterance_end', utterance_id=str(self.utterance_id), timestamp=timestamp))
                self.utterance_id += 1
                self.has_segments = False
        else:
            self.rest_since = None
            if self.start is not None:
                self.state = 'CAPTURING'
            elif self.state == 'READY':
                if self.onset_since is None:
                    self.onset_since = timestamp
                if timestamp-self.onset_since + 1e-9 >= self.config.onset:
                    self.start = self.onset_since
                    self.state = 'CAPTURING'
        return events

    def finish(self):
        return [self.close(self.last, 'incomplete', 'end_of_file')] if self.start is not None else []
