import math
from queue import Queue
from threading import Thread
from FcmManager import FcmManager
from Firestore import Firestore
import time

classNames = ["lie", "sit", "stand", ""]
# box = {{x1, y1}, {x2, y2}, cls}

class Processor(object):
    def __init__(self, duration=1):
        self.q = Queue()
        self.duration = duration
        self.prev = 3
        self.fcmManager = FcmManager()
        self.firestore = Firestore()
        self.prev = set()
        
        self.thread = Thread(target=self.process, args=())
        self.thread.daemon = True
        self.thread.start()


    def _get_dist(self, box1, box2):
        # get the euclidean dist between lt points
        return math.sqrt((box1[0][0] - box2[0][0])**2 + (box1[0][1] - box2[0][1])**2)
    
    def _group_similar_points(self, boxes, threshold = 0.07):
        groups = []
        
        for box in boxes:
            added_to_group = False
            for group in groups:
                group_type = group[0][2]
                if box[2] == group_type and any(self._get_dist(box, group_point) <= threshold for group_point in group):
                    group.append(box)
                    added_to_group = True
                    break
        
            if not added_to_group:
                groups.append([box])
        return groups
    
    def _get_center(self, point1, point2):
        return ((point1[0]+point2[0])/2, (point1[1]+point2[1])/2, point1[2])

    def _check_trigger(self, point):
        ret = []
        res = set()
        triggers = self.firestore.db.collection(u'trigger').get()

        for trigger_raw in triggers:
            trigger = trigger_raw.to_dict()
            if trigger['detect_posture'] == point[2] and trigger['lt_x'] <= point[0] <= trigger['rb_x'] and trigger['lt_y'] <= point[1] <= trigger['rb_y']:
                if not (trigger['routine_id'] in self.prev):
                    ret.append(trigger['routine_id'])
                set.add(trigger['routine_id'])
        
        self.prev = res

        return ret        

    def process(self):
        while True:
            boxes=list(self.q.queue)
            self.q = Queue()

            groups = self._group_similar_points(boxes)
            
            for group in groups:
                if len(group) > 10:
                    target = sorted(group)[len(group)//2]
                    target_center = self._get_center(target[0], target[1])
                    
                    routine_ids = self._check_trigger(target_center)

                    for routine_id in routine_ids:
                        self.fcmManager.send_fcm_message(routine_id)
        
            time.sleep(self.duration)

    def push(self, object):
        self.q.put(object)
        
        
    
