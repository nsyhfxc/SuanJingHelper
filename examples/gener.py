import random

random.seed()

t = 5
print(t)
for _ in range(t):
    for _ in range(3):
        print(" ".join(str(random.randint(1, 50)) for _ in range(5)))
