from fasthtml.common import *
from fastcore.xml import to_xml
from starlette.endpoints import WebSocketEndpoint
from starlette.routing import WebSocketRoute
import asyncio

css = Style('#grid { display: grid; grid-template-columns: repeat(20, 20px); grid-template-rows: repeat(20, 20px);gap: 1px; } .cell { width: 20px; height: 20px; border: 1px solid black; } .alive { background-color: green; } .dead { background-color: white; }')
gridlink = Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css", type="text/css")
htmx_ws = Script(src="https://unpkg.com/htmx-ext-ws@2.0.0/ws.js")
app = FastHTML(hdrs=(picolink, gridlink, css, htmx_ws))
rt = app.route

grid = [[0 for _ in range(20)] for _ in range(20)]
game_state = {'running': False}
def update_grid(grid: list[list[int]]) -> list[list[int]]:
    new_grid = [[0 for _ in range(20)] for _ in range(20)]
    def count_neighbors(x, y):
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        count = 0
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]): count += grid[nx][ny]
        return count
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            neighbors = count_neighbors(i, j)
            if grid[i][j] == 1:
                if neighbors < 2 or neighbors > 3: new_grid[i][j] = 0
                else: new_grid[i][j] = 1
            else:
                if neighbors == 3: new_grid[i][j] = 1
    return new_grid

def Grid():
    cells = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            cell_class = 'alive' if cell else 'dead'
            cell = Div(cls=f'cell {cell_class}', hx_put='/update', hx_vals={'x': x, 'y': y}, hx_swap='none', hx_target='#gol', hx_trigger='click')
            cells.append(cell)
    return Div(*cells, id='grid')

def Home():
    gol = Div(Grid(), id='gol', cls='row center-xs')
    run_btn = Button('Run', id='run', cls='col-xs-2', hx_put='/run', hx_target='#gol', hx_swap='none')
    pause_btn = Button('Pause', id='pause', cls='col-xs-2', hx_put='/pause', hx_target='#gol', hx_swap='none')
    reset_btn = Button('Reset', id='reset', cls='col-xs-2', hx_put='/reset', hx_target='#gol', hx_swap='none')
    return (Title('Game of Life'), Main(
            gol, Div(run_btn, pause_btn, reset_btn, cls='row center-xs'),
            hx_ext="ws", ws_connect="/gol"))

@rt('/')
def get(): return Home()

player_queue = []
async def on_connect(send): player_queue.append(send)
async def on_disconnect(send): player_queue.remove(send)

@app.ws('/gol', conn=on_connect, disconn=on_disconnect)
async def ws(msg:str, send): pass

async def background_task():
    global grid
    while True:
        if game_state['running'] and len(player_queue) > 0:
            grid = update_grid(grid)
            for player in player_queue: await player(Grid())
        await asyncio.sleep(1.0)

background_task_coroutine = asyncio.create_task(background_task())

@rt('/update')
async def put(x: int, y: int):
    grid[y][x] = 1 if grid[y][x] == 0 else 0
    for player in player_queue: await player(Grid())

@rt('/run')
async def put():
    game_state['running'] = True
    for player in player_queue: await player(Grid())

@rt("/reset")
async def put():
    global grid
    grid = [[0 for _ in range(20)] for _ in range(20)]
    game_state['running'] = False
    for player in player_queue: await player(Grid())

@rt('/pause')
async def put():
    game_state['running'] = False
    for player in player_queue: await player(Grid())

# run_uv()
# import uvicorn

# if __name__ == "__main__":
#     asyncio.run(background_task())
#     uvicorn.run(app, host="0.0.0.0", port=8000)