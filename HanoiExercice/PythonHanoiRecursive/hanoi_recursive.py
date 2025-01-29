ITERATION = 0
def hanoi(n, start, temp, goal):
    global ITERATION
    if n>0:
        hanoi(n-1, start, goal, temp)
        print(f'{ITERATION}: disk {n-1} move from {start} to {goal}')
        ITERATION += 1
        hanoi(n-1, temp, start, goal)

hanoi(20, "left", "middle", "right")
