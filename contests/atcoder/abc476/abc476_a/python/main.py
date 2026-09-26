import sys


def solve():
    input = sys.stdin.readline
    # Write your solution here.
    S = input()
    print(type(S))
    if S[-1] == "e":
        S = S + str("r")
    else:
        S = S + str("er")

    print(S)


if __name__ == "__main__":
    solve()
