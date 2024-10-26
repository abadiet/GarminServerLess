# GarminServerLess (GSL)

GSL is a Python library to fully use Garmin devices without sharing private information with Garmin.

<p align="center">
	<img src="https://github.com/abadiet/GarminServerLess/blob/main/resources/logo.png" width="200">
</p>

> [!WARNING]
> This project is still in very early stages of development.

> [!CAUTION]
> These tools are provided "as is" without any warranty. Using them can be dangerous for your device, so please be careful. You are solely responsible for any actions you take.


## Usage

```
from GSL import Device

myDevice = Device("/dev/ttyACM0")

session_cookie = "..." # cookie named "session" when logged in to apps.garmin.com. Can be any Garmin account, even a junk one

# install an app
myDevice.install(session_cookie, ciq_url="https://apps.garmin.com/apps/6b53eedd-bf67-4c18-a2d6-af1d59518357")

# get available updates
print(myDevice.get_updates_name(session_cookie)) # e.g. ['Time Zone Map', 'GPS Software', 'Fenix 7 Sensor Hub', 'Spotify']

# process specific updates
myDevice.update(names=['GPS Software', 'Spotify'], session_cookie=session_cookie)

# update all
myDevice.update(session_cookie)
```

## Reverse Engineering

GSL is heavily based on Garmin Express (GE), a Windows and macOS software provided by Garmin that allows you to update, sync, and register your devices.
GE is an old software with no significant obfuscation or high-security protections. It is coded in C#, a programming language that runs on the .NET framework, which makes reverse engineering easier as I can use a .NET decompiler, such as [ILSpy](https://github.com/icsharpcode/ILSpy). This is why I focused on this software instead of other Garmin facilities.


## Roadmap

- [x] Download Connect IQ apps binaries (using USB)
    - This still requires a junk account for now
    - I made an add-on dedicated to this: [LocalCIQ](https://addons.mozilla.org/en-US/firefox/addon/localciq/)
- [x] Edit Connect IQ apps settings (using USB)
- [ ] Edit/View metrics (using USB)
- [x] Update devices (using USB)
    - Only the firmwares and applications are supported for now
    - There are still some tricky things to fix
- [ ] Bye USB, Welcome Bluetooth
- [ ] Wifi support

## Related projects

Here are some interesting projects related to reverse engineering Garmin's systems:

- [Anvil Secure Blog](https://www.anvilsecure.com/blog/compromising-garmins-sport-watches-a-deep-dive-into-garminos-and-its-monkeyc-virtual-machine.html)
- [Freeyourgadget](https://codeberg.org/Freeyourgadget/Gadgetbridge/issues/959)
- [ConnectIQ Debugger](https://github.com/pzl/ciqdb)
- and many others...
