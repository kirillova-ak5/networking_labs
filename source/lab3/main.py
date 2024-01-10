import random
import time
from threading import Thread
import queue
import matplotlib.pyplot as plt


stop_all = False
SEG_NUMBER = 10
PC_NUMBER = 10
counter_s = 0
counter_f = 0

class Frame:
    def __init__(self):
        self.enabled_list = []
        self.has_matr = []
        self.conn = -1  # to
        self.seg = -1
        self.conn_result = False
        self.id = -1  # from
        self.iter = -1

    def join(self, other):
        if other.iter != self.iter or self.id == other.id:
            return
        if not (type(self.conn) is list):
            self.conn = [self.conn]
            self.conn_result = [self.conn_result]
            self.id = [self.id]
            self.seg = [self.seg]
        if not (type(other.conn) is list):
            other.conn = [other.conn]
            other.conn_result = [other.conn_result]
            other.id = [other.id]
            other.seg = [other.seg]
        self.conn += other.conn
        self.conn_result += other.conn_result
        self.id += other.id
        self.seg += other.seg

class Tracker:
    def __init__(self):
        self.pc_ids = []
        self.peers = {}
        self.enabled = {}
        self.frlist = []
        self.frlist2 = queue.SimpleQueue()

    def add_pc(self, id, enable, pc):
        self.pc_ids.append(id)
        self.enabled[id] = enable
        self.peers[id] = pc

    def get_pc(self, id):
        return self.peers[id]

    def set_pc_state(self, id, enabled):
        self.enabled[id] = enabled

    def get_enabled_list(self):
        en_list = []
        for p in self.pc_ids:
            if self.enabled[p]:
                en_list.append(p)
        return en_list

    def generate_frame(self):
        fr = Frame()
        fr.enabled_list = [self.enabled[i] for i in range(len(self.enabled))]
        for i in range(len(self.peers)):
            fr.has_matr.append(self.peers[i].has_segment.copy())
        return fr

class PC:
    def __init__(self, id):
        self.SEG_NUM = SEG_NUMBER
        self.DOWNLOAD_DELAY = 0.2
        self.id = id
        self.enable = True
        self.has_segment = [False for i in range(self.SEG_NUM)]

    def upload_file(self):
        self.has_segment = [True for i in range(self.SEG_NUM)]

    def send_segment(self, num):
        if not self.has_segment[num]:
            return False
        st = time.time()
        t = time.time()
        while t - st < self.DOWNLOAD_DELAY:
            if not self.enable:
                return False
            t = time.time()
        return True

    def needed_seg(self):
        nd = []
        for i in range(len(self.has_segment)):
            if not self.has_segment[i]:
                nd.append(i)
        return nd

    def find_rarest_needed(self, tracker):
        nd = self.needed_seg()
        if not nd:
            return None, None
        nlist = [0 if i in nd else -1 for i in range(self.SEG_NUM)]
        pc_has = [-1 for i in range(self.SEG_NUM)]
        pcs = tracker.get_enabled_list()
        if not pcs:
            return None, None
        for pc_id in pcs:
            pc = tracker.get_pc(pc_id)
            for i in range(len(pc.has_segment)):
                if nlist[i] != -1 and pc.has_segment[i]:
                    nlist[i] += 1
                    pc_has[i] = pc.id
        n = 1000
        for seg in nlist:
            if seg > 0 and seg < n:
                n = seg
        rarest = []
        pc_rarest = []
        for i in range(len(nlist)):
            if nlist[i] == n:
                rarest.append(i)
                pc_rarest.append(pc_has[i])
        if not rarest:
            return None, None
        idx = random.randint(0, len(rarest) - 1)
        return rarest[idx], pc_rarest[idx]

    def run(self, tracker):
        tracker.add_pc(self.id, True, self)
        #tracker.frlist.append(tracker.generate_frame())
        iter = -1
        while not stop_all:
            iter += 1
            delay = (250 + random.randint(0, 250)) / 1000.0
            time.sleep(delay)
            self.enable = random.randint(0, 2) != 0
            tracker.set_pc_state(self.id, self.enable)

            seg_to_download, seed_id, success = -1, -1, None
            if self.enable:
                seg_to_download, seed_id = self.find_rarest_needed(tracker)
                if seg_to_download is not None and seed_id is not None:
                    seed = tracker.get_pc(seed_id)
                    success = seed.send_segment(seg_to_download)
                    if success:
                        self.has_segment[seg_to_download] = True
                        global counter_s
                        counter_s += 1
                    else:
                        global counter_f
                        counter_f += 1

            fr = tracker.generate_frame()
            fr.conn = seed_id
            fr.seg = seg_to_download
            fr.conn_result = success
            fr.iter = iter
            fr.id = self.id
            tracker.frlist.append(fr)
            tracker.frlist2.put(fr)


def simulate(nseg, npc):
    global stop_all
    stop_all = False
    global counter_s
    counter_s = 0
    global counter_f
    counter_f = 0
    global SEG_NUMBER
    SEG_NUMBER = nseg

    num_pc = npc
    tracker = Tracker()
    computers = [PC(i) for i in range(num_pc)]
    computers[0].upload_file()

    st = time.time()
    peer_threads = [Thread(target=computers[i].run, args=(tracker,)) for i in range(len(computers))]
    for i in range(len(computers)):
        peer_threads[i].start()

    while True:
        if counter_s >= nseg * (npc - 1):
            stop_all = True
            break

    for i in range(len(peer_threads)):
        peer_threads[i].join()
    t = time.time()
    print(t - st)
    print(counter_f)
    return t - st, tracker.frlist2


def main1():
    times = [0 for npc in range(10)]
    c = 0
    for nseg in range(10):
        for repeat in range(10):
            times[nseg] += simulate((nseg + 1) * 5, 10) * 1000
            print(c)
            c += 1
        times[nseg] /= 10
    x1 = [(npc + 1) * 5 for npc in range(10)]
    plt.plot(x1, times)
    plt.show()

if __name__ == '__main__':
    t, frlist2 = simulate(4, 6)
    frlist = []
    while not frlist2.empty():
        frlist.append(frlist2.get())

    fin_frlist = []
    for i in range(len(frlist)):
        if frlist[i].id == 1:
            fin_frlist.append(frlist[i])
    for i in range(len(fin_frlist)):
        for j in range(len(frlist)):
            fin_frlist[i].join(frlist[j])

    vert_x = [0, 1, 1.5, 1, 0, -0.5]
    vert_y = [0, 0, 0.87, 1.73, 1.73, 0.87]

    gx = []
    gy = []
    rx = []
    ry = []
    for i in range(len(fin_frlist[0].enabled_list)):
        if fin_frlist[0].enabled_list[i]:
            gx.append(vert_x[i])
            gy.append(vert_y[i])
        else:
            rx.append(vert_x[i])
            ry.append(vert_y[i])

    for iter in range(len(fin_frlist)):
        plt.scatter(rx, ry, marker="X", color="red")
        plt.scatter(gx, gy, marker="o", color="green")
        id1 = 0
        id2 = 3
        props = dict(boxstyle='round', facecolor='silver', alpha=0.5)
        for ps_id in range(len(fin_frlist[iter].has_matr)):
            for seg_id in range(len(fin_frlist[iter].has_matr[ps_id])):
                if fin_frlist[iter].has_matr[ps_id][seg_id]:
                    plt.text(vert_x[ps_id] + 0.09 * (seg_id - 1), vert_y[ps_id] - 0.12, str(seg_id), bbox = props)
        for con_id in range(len(fin_frlist[iter].conn)):
            if fin_frlist[iter].conn[con_id] is not None and fin_frlist[iter].conn[con_id] != -1:
                if fin_frlist[iter].conn_result[con_id] is True:
                    clr = "green"
                else:
                    clr = "red"
                plt.plot([vert_x[fin_frlist[iter].conn[con_id]], vert_x[fin_frlist[iter].id[con_id]]],
                        [vert_y[fin_frlist[iter].conn[con_id]], vert_y[fin_frlist[iter].id[con_id]]], color=clr)
                plt.text((vert_x[fin_frlist[iter].conn[con_id]] + vert_x[fin_frlist[iter].id[con_id]]) / 2,
                         (vert_y[fin_frlist[iter].conn[con_id]] + vert_y[fin_frlist[iter].id[con_id]]) / 2 - 0.1,
                         str(fin_frlist[iter].seg[con_id]), bbox=props)

        plt.ylim(-0.25, 2.25)
        plt.xlim(-0.75, 1.75)
        plt.figure()

    plt.show()

    print("")
    input()
    print("")
