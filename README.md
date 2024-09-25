# GarminServerLess (GSL)

GSL is a Python library to fully use Garmin devices without using Garmin servers.

> [!WARNING]
> This project is still in very early stages of development.

> [!CAUTION]
> These tools are provided "as is" without warranty of any kind. Using them can be dangerous for your device: please be careful as you are the only responsible for what you are doing.


## Usage

```
from gsl import App, CIQ

# Print the device names
print(CIQ.get_devices_names())

# Download the latest Strava app and edit its settings 
strava = App(ciq_url="https://apps.garmin.com/apps/6b53eedd-bf67-4c18-a2d6-af1d59518357")
strava.download("fēnix® 7X Pro", "strava.PRG", session_cookie)
strava.download_settings("fēnix® 7X Pro", "strava.SET")
```

## Reverse Engineering

GSL is higly based on Garmin Express (GE), a Windows and MAC OS software provided by Garmin that enables you to update, sync and register your devices.
GE is a pretty old software without any kind of obfuscation or high security protections. Moreover, it has been codded in C#, a programming language that runs on the .NET framework which ease the reverse engineering as I can use a .NET decompiler such as [ILSpy](https://github.com/icsharpcode/ILSpy). This is why I focused on this software instead of other Garmin facilities.


## Roadmap

- [x] Download Connect IQ apps binaries (using USB)
    - It still needs a junk account for now
    - I made an add-on dedicated to this [LocalCIQ](https://addons.mozilla.org/en-US/firefox/addon/localciq/)
- [x] Edit Connect IQ apps settings (using USB)
- [ ] Edit/View metrics (using USB)
- [ ] Update devices (using USB)
- [ ] Bye USB, Welcome Bluetooth

## Related projects

Here are some interesting projects when reverse engineering Garmin's systems.

- [Anvil Secure Blog](https://www.anvilsecure.com/blog/compromising-garmins-sport-watches-a-deep-dive-into-garminos-and-its-monkeyc-virtual-machine.html)
- [Freeyourgadget](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/959)
- [ConnectIQ Debugger](https://github.com/pzl/ciqdb)
- and many others...
