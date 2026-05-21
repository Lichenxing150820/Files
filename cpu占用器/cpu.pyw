import multiprocessing
import time

def cpu_stress(target_percent=50):
    while True:
        start_time = time.time()
        # 计算忙等待时间
        while time.time() - start_time < target_percent / 100:
            pass  # 占用 CPU
        time.sleep(1 - target_percent / 100)  # 休眠剩余时间

if __name__ == "__main__":
    num_cores = multiprocessing.cpu_count()
    processes = []
    
    for _ in range(num_cores):
        p = multiprocessing.Process(target=cpu_stress, args=(50,))  # 50% 占用
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
