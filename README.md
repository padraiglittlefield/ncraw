# ncraw
Linux CLI for the NiteCrawler Focuser

## Install

Put `ncraw`, `ncraw.1`, and `install.sh` in the same folder, then run:

```
sudo bash install.sh
```

## Usage

```
ncraw where                   show focus and rotation position
ncraw where focus|rotation    show one axis

ncraw focus <steps>           move focus to position
ncraw rotate <steps>          move rotation to position

ncraw stop                    stop both motors
ncraw stop focus|rotation     stop one motor

ncraw jog focus|rotation <delta>
                              move by a relative amount (+/- steps)
```

## Examples

```
ncraw where
ncraw focus 500
ncraw rotate -90
ncraw jog focus 100
ncraw jog rotation -10
ncraw stop
```

## GUI

```
pip install PyQt5
python3 gui.py
```

The GUI shells out to the `ncraw` CLI for every action. It includes
fixed-step jog buttons (`−` / `+`) with a step-size selector per axis,
and remembers the last "set position" values and jog step sizes between
launches in `~/.config/ncraw/gui_state.json`.

## Device

By default ncraw uses `/dev/ttyUSB0`. If your focuser is on a different port:

```
NCRAW_DEVICE=/dev/ttyUSB1 ncraw where
```

## Manual

```
man ncraw
```
