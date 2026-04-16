# ncraw
Linux CLI for the Nightcrawler Focuser

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
```

## Examples

```
ncraw where
ncraw focus 500
ncraw rotate -90
ncraw stop
```

## Device

By default ncraw uses `/dev/ttyUSB0`. If your focuser is on a different port:

```
NCRAW_DEVICE=/dev/ttyUSB1 ncraw where
```

## Manual

```
man ncraw
```