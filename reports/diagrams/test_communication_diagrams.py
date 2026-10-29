import math
import unittest

from export_communication_diagrams import composition, hardware, research, baseline, esp32


class DiagramChecks(unittest.TestCase):
    def test_connectors_do_not_cross_unrelated_blocks(self):
        for factory in (composition, hardware, research, baseline, esp32):
            page = factory()
            for source, target, points in page.routes:
                for a, b in zip(points, points[1:]):
                    samples = max(2, int(math.dist(a, b) / 3))
                    for step in range(samples + 1):
                        t = step / samples
                        px, py = a[0] + t*(b[0]-a[0]), a[1] + t*(b[1]-a[1])
                        for name, node in page.nodes.items():
                            if name in (source, target):
                                continue
                            x,y,w,h = node['rect']
                            self.assertFalse(x+2 < px < x+w-2 and y+2 < py < y+h-2,
                                             f'{factory.__name__}: {source}→{target} crosses {name}')

    def test_flush_and_playback_are_separate(self):
        page = composition()
        graph = {(a,b) for a,b,_ in page.edges}
        self.assertIn(('transfer','snapshot'), graph)
        self.assertIn(('transfer','newdraft'), graph)
        self.assertIn(('snapshot','tts'), graph)
        self.assertIn(('play','idle'), graph)
        self.assertIn(('play','request'), graph)
        self.assertIn(('request','stop'), graph)
        self.assertNotIn(('stop','newdraft'), graph)

    def test_exports_have_distinct_hardware_scope(self):
        page = hardware()
        self.assertNotIn('esp', page.nodes)
        self.assertIn('esp', esp32().nodes)
        for name in ('app','models','ui','agent'):
            x,y,w,h = page.nodes[name]['rect']
            self.assertTrue(70 <= x and x+w <= 1730 and 530 <= y and y+h <= 1280)


if __name__ == '__main__':
    unittest.main()
