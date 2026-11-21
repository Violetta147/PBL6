import unittest
from .segmenter import Segmenter

class SegmentationTests(unittest.TestCase):
    def test_hold_repeat_and_end(self):
        s=Segmenter(); events=[]
        for i in range(100):
            active=10<=i<30 or 45<=i<65
            events.extend(s.feed(i/10,['active' if active else 'rest','rest']))
        complete=[e for e in events if e.get('status')=='complete']
        self.assertEqual(len(complete),2)
        self.assertNotEqual(complete[0]['segment_id'],complete[1]['segment_id'])
        self.assertAlmostEqual(complete[0]['movement_start'],1.)
        self.assertAlmostEqual(complete[0]['end'],3.2)
    def test_missing_is_not_rest(self):
        s=Segmenter(); events=[]
        for i in range(30):
            arms=['rest','rest'] if i<10 else ['active','rest'] if i<20 else [None,None]
            events.extend(s.feed(i/10,arms))
        self.assertEqual([e['status'] for e in events],['incomplete'])
    def test_eof(self):
        s=Segmenter()
        for i in range(20):
            s.feed(i/10,['rest','rest'] if i<10 else ['active','active'])
        self.assertEqual(s.finish()[0]['reason'],'end_of_file')
    def test_timestamp_validation(self):
        s=Segmenter();s.feed(0,['rest','rest'])
        with self.assertRaises(ValueError):s.feed(0,['rest','rest'])

if __name__=='__main__':unittest.main()
