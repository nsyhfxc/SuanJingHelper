t = int(input())
for i in range(t):
    l1 = list(map(int,input().split()))
    l2 = list(map(int,input().split()))
    l3 = list(map(int,input().split()))
    res = sum(l1)
    if res > 80:
        res += sum(l2)
        if sum(l2) > 40:
            res += sum(l3)
    print(res)
