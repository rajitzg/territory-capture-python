# Candidate Guide

Write your logic in `candidate/candidate_controller.py`. That's the exact
file the framework calls.

You don't need to touch anything outside `candidate/`. If you want more
modules, add them in there too — that folder is yours to extend however
you like. Nothing outside it needs to change, and nothing outside it
should.

Inside `candidate/`, `examples/` has a couple of read-only implementations
that only demonstrate the mechanics — not a strategy worth copying.
There's also an opponent to practice against, shown as "Enemy State Machine"
in the GUI.

## The rules

- You move one step at a time: NORTH, SOUTH, EAST, or WEST.
- Step outside your own territory → you start (or extend) a trail.
- Step back onto territory you own → your trail closes and becomes
  territory. Anything it surrounds becomes yours too, including enemy
  territory.
- Step on your own trail → you die.
- Step on the enemy's trail → they die, you're fine.
- Dying sends you back to your starting zone. You keep playing after that.
- The match ends when both players run out of turns. Most territory wins.
- A move can be `INVALID` (off the board, or into the opponent's current
  spot). Nothing happens, and you get asked to move again.

## `AgentController`

This is the abstract base class `CandidateController` implements
(`territorygame.api.agent_controller.AgentController`).

### take_turn(game)
```python
def take_turn(self, game: GameApi) -> None
```
Put your decision-making here. You never call this method yourself. The
framework calls it for you, whenever it's your turn.

`game` (a `GameApi`, see below) is your window into the current turn: where
you are, what you can see, how the match stands. Read what you need from
it, decide on a direction, then call `game.move(direction)` **exactly
once**. That call is your whole turn. `take_turn` doesn't return anything;
`move()` is how you actually act.

If the direction you pick comes back `INVALID`, nothing happens and
`take_turn` is called again right away so you can try something else, same
turn.

### get_debug_state()
```python
def get_debug_state(self) -> str | None:
    return None  # the default
```
Optional. Override and return a short label for whatever state you think
you're in (an enum's `.name` works well), and the GUI shows it next to
your player card. Handy for watching a match and seeing what your
controller is "thinking." No effect on gameplay either way.

## `GameApi`

Your one-turn snapshot of the match. Read what you need, then call
`game.move(direction)` once.

### get_agent_position()
```python
def get_agent_position(self) -> GridPosition
```
Where you are right now.

### get_respawn_position()
```python
def get_respawn_position(self) -> GridPosition
```
Where you reappear after dying.

### get_owned_territory_cell_count()
```python
def get_owned_territory_cell_count(self) -> int
```
How many cells you currently own.

### get_opponent_territory_cell_count()
```python
def get_opponent_territory_cell_count(self) -> int
```
How many cells the opponent currently owns.

### get_remaining_turns()
```python
def get_remaining_turns(self) -> int
```
How many turns you have left.

### get_active_trail()
```python
def get_active_trail(self) -> list[GridPosition]
```
Your current trail, oldest cell first. Empty if you're standing on your
own territory right now.

### get_visible_grid()
```python
def get_visible_grid(self) -> tuple[tuple[VisibleCell, ...], ...]
```
The cells you can currently see, centered on you. Index it `[y][x]`. Each
`VisibleCell` carries its real board position too, so you never have to
convert window coordinates to board coordinates yourself.

### get_board_width() / get_board_height()
```python
def get_board_width(self) -> int
def get_board_height(self) -> int
```
The size of the whole board (not just what you can see).

### move(direction)
```python
def move(self, direction: Direction) -> MoveResult
```
Try to move one step. Returns what happened.

## Types

### GridPosition
```python
@dataclass(frozen=True)
class GridPosition:
    x: int
    y: int
```
A cell on the board. `(0, 0)` is the top-left corner.

### VisibleCell
```python
@dataclass(frozen=True)
class VisibleCell:
    position: GridPosition
    occupant: OccupantView
    territory: TerritoryView
```
One cell you can see. `occupant` is the head/trail layer; `territory` is
the land underneath. Both are always present — a trail does not hide
territory.

### Direction
```python
class Direction(Enum):
    NORTH = auto()
    SOUTH = auto()
    EAST = auto()
    WEST = auto()
```

### MoveResult
```python
class MoveResult(Enum):
    MOVED = auto()
    CAPTURED = auto()
    DIED = auto()
    INVALID = auto()
```
What `move()` just did: `MOVED` (normal step), `CAPTURED` (your trail
closed), `DIED` (you hit a trail), or `INVALID` (nothing happened).

### OccupantView
```python
class OccupantView(Enum):
    EMPTY = auto()
    SELF_TRAIL = auto()
    OPPONENT_TRAIL = auto()
    SELF_AGENT = auto()
    OPPONENT_AGENT = auto()
```
What's standing or trailing on the cell. You'll never see the opponent's
real player number, only `SELF_*` or `OPPONENT_*`. An agent standing on a
trail shows as the agent, not the trail.

### TerritoryView
```python
class TerritoryView(Enum):
    UNOWNED = auto()
    SELF = auto()
    OPPONENT = auto()
```
Who owns the land. Independent of `occupant`. Empty unowned space is
`(EMPTY, UNOWNED)`.

## Helpers (`territorygame.helpers`)

Basic board math you shouldn't have to write yourself. Free to use from
`candidate_controller.py`.

### movement_utils.next_position
```python
def next_position(position: GridPosition, direction: Direction) -> GridPosition
```
The cell one step away in a direction.

### movement_utils.is_within_board
```python
def is_within_board(position: GridPosition, width: int, height: int) -> bool
```
Is this cell actually on the board?

### movement_utils.is_valid_move
```python
def is_valid_move(game: GameApi, direction: Direction) -> bool
```
Would this move be on the board and not walk into the opponent's agent?
**This does not check trails.** Walking into your own trail (or theirs)
still counts as "valid" here. That part is on you.

### movement_utils.valid_directions
```python
def valid_directions(game: GameApi) -> list[Direction]
```
All directions that pass `is_valid_move` right now.

### movement_utils.manhattan_distance
```python
def manhattan_distance(a: GridPosition, b: GridPosition) -> int
```
Grid distance between two cells (no diagonals).

### movement_utils.find_cell
```python
def find_cell(visible_grid: tuple[tuple[VisibleCell, ...], ...], position: GridPosition) -> VisibleCell | None
```
Look up one cell in a visible grid by its board position.

### movement_utils.random_direction
```python
def random_direction(rng: random.Random) -> Direction
```
Picks one of the four directions at random.

### ObservedBoard
```python
ObservedBoard(width: int, height: int)
def update(self, visible_grid: tuple[tuple[VisibleCell, ...], ...]) -> None   # call this each turn
def get(self, position: GridPosition) -> VisibleCell | None
def has_observed(self, position: GridPosition) -> bool
def clear(self) -> None
```
Remembers the last thing you saw at each cell, so you can reason about
parts of the board outside your current window. It only remembers what
you've actually seen. It won't guess whether a cell has changed since.

## Tips

Nothing below is solved for you in the example controllers. Worth thinking
about once the basics are working:

- **Avoid your own trail.** `is_valid_move` only checks board bounds and
  the opponent's agent; stepping on your own trail still passes it, but it
  kills you.
- **Watch for the opponent's trail too.** Crossing it kills *them*, and
  their agent's position hints at where their trail might be.
- **Aggression vs. caution.** Compare `get_owned_territory_cell_count()`
  to `get_opponent_territory_cell_count()`. Ahead, maybe hunt for a kill;
  behind, maybe play safer.
- **Getting home efficiently.** `get_respawn_position()` isn't necessarily
  your nearest owned cell once you've captured territory elsewhere.
  Scanning `get_visible_grid()` for the nearest `TerritoryView.SELF` cell
  can do better.
- **Trail length is a trade-off.** Longer trails claim more area on
  capture but leave you exposed for longer.
- **Remember what you've seen.** `ObservedBoard` builds a picture beyond
  your current visible window, useful for planning ahead.
- **Remaining turns matter.** Early vs. late game might call for
  different behavior. `get_remaining_turns()` tells you where you stand.
