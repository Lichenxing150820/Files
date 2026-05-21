import traceback

while True:
    a=input('算式：，输入exit()退出')
    try:
        n=eval(a)
        print(n)
    except Exception:
        traceback.print_exc()
