from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WIDTH, HEIGHT = 10, 10
NUM_MUTATIONS = 8


def create_grid():
    grid = [["empty" for _ in range(WIDTH)] for _ in range(HEIGHT)]
    mutation_positions = set()
    while len(mutation_positions) < NUM_MUTATIONS:
        x, y = random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1)
        if (x, y) != (0, 0):
            mutation_positions.add((x, y))
    for x, y in mutation_positions:
        grid[y][x] = "mutation"
    grid[0][0] = "dna_source"  # base always has dna source
    return grid, mutation_positions


def reset():
    global state
    grid, mutation_positions = create_grid()
    state = {
        "grid": grid,
        "agent": [0, 0],
        "steps": 0,
        "mutationsLeft": len(mutation_positions),
        "mutationPositions": mutation_positions,
        "visited": set([(0, 0)]),
        "carryingDNA": False,
        "repairComplete": False,
        "reward": 0.0,
        "mode": "to_base",  # to_base, search, to_mutation
        "discoveredMutations": set()
    }


reset()


def valid(x, y):
    return 0 <= x < WIDTH and 0 <= y < HEIGHT


def neighbors(x, y):
    return [
        (x + dx, y + dy)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if valid(x + dx, y + dy)
    ]


def move_towards(target):
    x, y = state["agent"]
    tx, ty = target
    if tx > x:
        return x + 1, y
    if tx < x:
        return x - 1, y
    if ty > y:
        return x, y + 1
    if ty < y:
        return x, y - 1
    return x, y


def choose_move():
    x, y = state["agent"]

    if state["repairComplete"]:
        return x, y

    # Discover mutation if present
    if state["grid"][y][x] == "mutation":
        state["discoveredMutations"].add((x, y))

    # Return to base to get DNA cell
    if not state["carryingDNA"] and (x, y) != (0, 0):
        state["mode"] = "to_base"
        return move_towards((0, 0))

    # At base to pick up DNA cell
    if not state["carryingDNA"] and (x, y) == (0, 0):
        state["carryingDNA"] = True
        state["mode"] = "search"

    # If at a discovered mutation and carrying DNA, repair
    if state["carryingDNA"] and (x, y) in state["discoveredMutations"]:
        state["discoveredMutations"].remove((x, y))
        state["mutationPositions"].remove((x, y))
        state["grid"][y][x] = "empty"
        state["mutationsLeft"] -= 1
        state["carryingDNA"] = False
        state["reward"] += 10.0
        if state["mutationsLeft"] == 0:
            state["repairComplete"] = True
        return move_towards((0, 0))

    # Head toward known mutation if any
    if state["carryingDNA"] and state["discoveredMutations"]:
        target = min(
            state["discoveredMutations"],
            key=lambda pos: abs(pos[0] - x) + abs(pos[1] - y)
        )
        return move_towards(target)

    # Random explore if carrying DNA and no known mutations
    unexplored = [
        (nx, ny)
        for nx, ny in neighbors(x, y)
        if (nx, ny) not in state["visited"]
    ]
    if unexplored:
        return random.choice(unexplored)

    return random.choice(neighbors(x, y))


@app.get("/state")
def get_state():
    return state


@app.get("/step")
def step():
    if state["repairComplete"]:
        return state
    x, y = choose_move()
    state["agent"] = [x, y]
    state["visited"].add((x, y))
    state["steps"] += 1
    state["reward"] -= 0.05
    return state


@app.post("/restart")
def restart():
    reset()
    return state

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
