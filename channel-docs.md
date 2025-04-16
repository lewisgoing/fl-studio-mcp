Properties
==========

Function definitions for managing channel properties.

### Examples

Make all of the selected channels purple

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)import  channels [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2) [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)for i in range(channels.channelCount()):
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    if channels.isChannelSelected(i):
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)        channels.setChannelColor(i, 0x9648aa) `

selectedChannel
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)selectedChannel(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    canBeNone: bool = False,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    offset: int = 0,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    indexGlobal: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> int `

Returns the index of the first selected channel, otherwise the nth selected channel where n is `offset` + 1. If n is greater than the number of selected channels, the global index of the last selected channel will be returned. If `indexGlobal` is set to `1`, this will replicate the behavior of [`channels.channelNumber()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#channels.__properties.channelNumber) by returning global indexes.

#### Note

-   This function replaces the functionality of `channelNumber()` entirely, with the added functionality of providing indexes respecting groups (when `indexGlobal` is not set).

#### Args

-   `canBeNone` (`bool`, optional): Whether the function will return `-1` or `0` when there is no selection. Defaults to `False` (returning `0`).

-   `offset` (`int`, optional): return other selected channels after offset. Defaults to 0.

-   `indexGlobal` (`bool`, optional): Whether to return the group index (`False`) or the global index (`True`).

#### Returns

-   `int`: index of first selected channel.

Included since API version 5

channelNumber
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)channelNumber(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    canBeNone: bool = False, offset: int = 0 [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Returns the global index of the first selected channel, otherwise the nth selected channel where n is `offset` + 1. If n is greater than the number of selected channels, the global index of the last selected channel will be returned.

If `canBeNone` is `1`, no selection will return `-1`. Otherwise, no selection will return `0` (representing the first channel).

#### Args

-   `canBeNone` (`bool`, optional): Whether the function will return `-1` or `0` when there is no selection. Defaults to `False` (returning `0`).

-   `offset` (`int`, optional): return other selected channels after offset. Defaults to 0.

#### Returns

-   `int`: global index of first selected channel.

Included since API version 1.

channelCount
------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)channelCount(globalCount: bool = False) -> int `

Returns the number of channels on the channel rack. Respect for groups is controlled by the `mode` flag.

#### Args

-   `globalCount` (`bool`, optional): Whether the number of channels should be global. Defaults to `False` (groups respected).

#### Returns

-   `int`: number of channels.

Included since API version 1. (updated with optional parameter in API version 3).

getChannelName
--------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelName(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> str `

Returns the name of the channel at `index`.

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting the channel name.

#### Returns:

-   `str`: channel name.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

setChannelName
--------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setChannelName(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, name: str, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> None `

Sets the name of the channel at `index`.

If a channel's name is set to "", its name will be set to the default name of the plugin or sample.

#### Args

-   `index` (`int`): index of channel.

-   `name` (`str`): new name for channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when setting the channel name.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelColor
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelColor(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Returns the color of the channel at `index`.

Note that colors can be split into or built from components using the functions provided in the [`utils`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils) module.

-   [`utils.ColorToRGB()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils.ColorToRGB)

-   [`utils.RGBToColor()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils.RGBToColor)

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting the channel color.

#### Returns:

-   `int`: channel color (0x--BBGGRR).

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

setChannelColor
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setChannelColor(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, color: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> None `

Sets the color of the channel at `index`.

Note that colors can be split into or built from components using the functions provided in the [`utils`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils) module.

-   [`utils.ColorToRGB()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils.ColorToRGB)

-   [`utils.RGBToColor()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/utils/#utils.RGBToColor)

#### Args

-   `index` (`int`): index of channel.

-   `color` (`int`): new color for channel (0x--BBGGRR).

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when setting the channel color.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

isChannelMuted
--------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)isChannelMuted(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> bool `

Returns whether channel is muted (`True`) or not (`False`).

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting the channel's mute status.

#### Returns

-   `bool`: mute status.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

muteChannel
-----------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)muteChannel(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    value: int = -1,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> None `

Toggles the mute state of the channel at `index`.

#### Args

-   `index` (`int`): index of channel.

-   `value` (`int`, optional): new value for mute state.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when muting channel.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

isChannelSolo
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)isChannelSolo(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> bool `

Returns whether channel is solo (`True`) or not (`False`).

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting channel solo status.

#### Returns

-   `bool`: solo status.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

soloChannel
-----------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)soloChannel(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> None `

Toggles the solo state of the channel at `index`.

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when soloing channel.

Included since API version 1

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelVolume
----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelVolume(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    mode: bool = False,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> float `

Returns the normalized volume of the channel at `index`, where `0.0` is the minimum value, and `1.0` is the maximum value. Note that the default volume for channels is defined in [`midi.ChannelDefaultVolume`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/miscellaneous/#midi.__miscellaneous.ChannelDefaultVolume).

By setting the `mode` flag to `True`, the volume is returned in decibels.

#### Args

-   `index` (`int`): index of channel.

-   `mode` (`int`, optional): whether to return as a float between 0 and 1 (`False`) or a value in dB (`True`). Defaults to `False`.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting channel volume.

#### Returns

-   `float`: channel volume.

Included since API version 1

#### API Changes

-   v33: add `useGlobalIndex` flag.

setChannelVolume
----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setChannelVolume(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    volume: float,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    pickupMode: int = midi.PIM_None,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-6)) -> None `

Sets the normalized volume of the channel at `index`, where `0.0` is the minimum value, and `1.0` is the maximum value. Note that the default volume for channels is defined in [`midi.ChannelDefaultVolume`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/miscellaneous/#midi.__miscellaneous.ChannelDefaultVolume). Use the pickup mode flag to set pickup options.

#### Args

-   `index` (`int`): index of channel.

-   `volume` (`float`): channel volume.

-   `pickupMode` (`int`, optional): define the pickup behavior. Refer to the [pickup modes documentation](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/pickup%20modes).

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when setting channel volume.

Included since API version 1

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelPan
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelPan(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> float `

Returns the normalized pan of the channel at `index`, where `-1.0` is 100% left, and `1.0` is 100% right. Note that the default pan for channels is `0.0` (centered).

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting channel pan.

#### Returns

-   `float`: channel pan.

Included since API version 1

#### API Changes

-   v33: add `useGlobalIndex` flag.

setChannelPan
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setChannelPan(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    pan: float,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    pickupMode: int = midi.PIM_None,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-6)) -> None `

Sets the normalized pan of the channel at `index`, where `-1.0` is 100% left, and `1.0` is 100% right. Note that the default pan for channels is `0.0` (centered). Use the pickup mode flag to set pickup options.

#### Args

-   `index` (`int`): index of channel.

-   `pan` (`float`): channel pan.

-   `pickupMode` (`int`, optional): define the pickup behavior. Refer to the [pickup modes documentation](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/pickup%20modes).

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when setting channel pan.

Included since API version 1

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelPitch
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelPitch(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    mode: Literal[1, 2],
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> int `

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelPitch(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    mode: Literal[0] = 0,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> float `

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelPitch(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, mode: int = 0, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> float | int `

Returns the current pitch bend (or range) of the channel at `index`. The `mode` parameter is used to determine the type of pitch returned.

#### Args

-   `index` (`int`): index of channel.

-   `mode` (`int`, optional):

    -   `0` (default): return the current pitch bend as a factor of the current range (usually `-1.0` to `1.0`). Larger values might be reached if the pitch is automated with events, for example.

    -   `1`: return the current pitch offset in cents.

        -   BUG: Official API docs incorrectly state "semitones".
    -   `2`: return the current pitch range in semitones.

        -   BUG: This is not guaranteed to be correct. For more information, see `setChannelPitch` on modifying the pitch range of a channel.
-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when getting channel pitch.

#### Returns

-   `float`: channel pitch (when `mode` is `0`).

-   `int`: channel pitch range (when `mode` is `1` or 2).

Included since API version 8.

#### API Changes

-   v33: add `useGlobalIndex` flag.

setChannelPitch
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setChannelPitch(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    value: float,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    mode: int = 0,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)    pickupMode: int = midi.PIM_None,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-6)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-7)) -> None `

Sets the pitch of the channel at `index` to value. The `mode` parameter is used to determine the type of pitch set. Use the pickup mode flag to set pickup options. The final pitch will be clamped to the current pitch range.

#### Args

-   `index` (`int`): index of channel.

-   `value` (`float`): value to set.

-   `mode` (`int`, optional):

    -   `0` (default): set pitch as a factor of the current pitch bend range (between [-1.0, 1.0]).

    -   `1`: set pitch in cents.

    -   `2`: **UTTERLY BROKEN.** Set the pitch range in semitones.

        BUG: This only affects the range reported by `getChannelPitch`. This will desynchronize the reported range from what is visible in the UI.

-   `pickupMode` (`int`, optional): define the pickup behavior. Refer to the [pickup modes documentation](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/pickup%20modes).

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when setting channel pitch.

Included since API version 8.

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelType
--------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelType(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Returns the type of instrument loaded into the channel rack at `index`.

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when querying channel type.

#### Returns

-   `int`: type of channel, one of the [channel type constants](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/midi/channel%20types).

Included since API Version 19.

#### API Changes

-   v33: add `useGlobalIndex` flag.

isChannelSelected
-----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)isChannelSelected(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> bool `

Returns whether the channel at `index` is selected.

#### Args

-   `index` (`int`): channel index.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index.

#### Returns

-   `bool`: whether the channel is selected.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

selectOneChannel
----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)selectOneChannel(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> None `

Exclusively select the channel at `index` (deselecting any other selected channels).

Using global indexes to select a channel outside of the current group deselects all channels.

#### Args

-   `index` (`int`): channel index.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when selecting channels.

Included since API version 8.

#### API Changes

-   v33: add `useGlobalIndex` flag.

selectChannel
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)selectChannel(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    value: int = -1,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> None `

Select the channel at `index` (respecting groups).

Using global indexes to select a channel outside of the current group has no effect.

#### Args

-   `index` (`int`): channel index.

-   `value` (`int`, optional): Whether to select or deselect the channel.

    -   `-1` (default): Toggle

    -   `0` : Deselect

    -   `1`: Select

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when selecting channels.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

selectAll
---------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)selectAll() -> None `

Selects all channels in the current channel group.

Included since API version 1.

deselectAll
-----------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)deselectAll() -> None `

Deselects all channels in the current channel group.

Included since API version 1.

getChannelMidiInPort
--------------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelMidiInPort(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Returns the MIDI-in port associated with the channel at `index`.

Channel MIDI-in ports can be used to send data directly to channels. Although channels are unassigned by default, a user can configure plugins to receive MIDI on a certain channel which can unlock many useful plugin-specific features.

Note that triggering notes using `channels.midiNoteOn` means that this functionality may be lost, so developers should take care to ensure that `getChannelMidiInPort` is checked to ensure that scripts don't inadvertently override this behavior.

#### Args

-   `index` (`int`): channel index.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index when querying channel MIDI-in port.

#### Returns

-   `int`: MIDI port associated with channel.

-   `-3`: Channel receiving notes from touch keyboard.

-   `-2`: Channel not assigned to a MIDI port.

-   `-1`: Channel receiving notes from typing keyboard.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

getChannelIndex
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getChannelIndex(index: int) -> int `

Returns the global index of a channel given the group `index`.

#### Args

-   `index` (`int`): index of channel (respecting groups).

#### Returns

-   `int`: global index of channel.

Included since API version 1.

getTargetFxTrack
----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getTargetFxTrack(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Returns the mixer track that the channel at `index` is linked to.

#### Args

-   `index` (`int`): index of channel.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index.

#### Returns

-   `int`: index of targeted mixer track.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

setTargetFxTrack
----------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)setTargetFxTrack(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    channelIndex: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)    mixerIndex: int,
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)    useGlobalIndex: bool = False, [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)) -> None `

Sets the mixer track that the channel at `index` is linked to.

#### Args

-   `channelIndex` (`int`): index of channel to link from.

-   `mixerIndex` (`int`): index of mixer track to link to.

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index.

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

getRecEventId
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)getRecEventId(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    index: int, useGlobalIndex: bool = False [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Return the starting point of REC event IDs for the channel at `index`.

See the [event mapping tutorial](https://il-group.github.io/FL-Studio-API-Stubs/tutorials/event_mapping). for more information on REC events.

#### Args

-   `index` (`int`): channel index

-   `useGlobalIndex` (`bool`, optional): whether to use the global channel index.

#### Returns

-   `int`: REC event ID offset for accessing `midi.REC_Chan_*` parameters

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

incEventValue
-------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)incEventValue(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    eventId: int, step: int, res: float = 1 / 24 [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Get event value increased by step.

This can be used to map encoder-style controls to events, by allowing them to adjust a parameter using a delta value.

Use result as new value in [`general.processRECEvent()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/general/fl%20state/#general.__fl_state.processRECEvent).

#### Example usage

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)# Increases the volume of channel 0 by a small delta of 1 [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)delta = 1 [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)# Calculate the event ID for the volume of channel 0 [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-4)event_id = midi.REC_Chan_Vol + channels.getRecEventId(0) [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-5)# Get the value adjusted by the delta [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-6)new_value = channels.incEventValue(event_id, delta) [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-7)# Process the new value [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-8)general.processRECEvent(event_id, new_value, midi.REC_UpdateValue | midi.REC_UpdateControl) `

#### Args

-   `eventId` (`int`): event ID (see the [event mapping tutorial](https://il-group.github.io/FL-Studio-API-Stubs/tutorials/event_mapping)).

-   `step` (`int`): delta value for the event.

-   `res` (`float`, optional): increment resolution, used as a multiplier to ensure that encoders are responsive. Defaults to `1/24`.

#### Returns

-   `int`: incremented event value, for use in [`general.processRECEvent()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/general/fl%20state/#general.__fl_state.processRECEvent).

Included since API version 1.

#### API Changes

-   v33: add `useGlobalIndex` flag.

processRECEvent
---------------

`[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-1)processRECEvent(
[](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-2)    eventId: int, value: int, flags: int [](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/channels/properties/#__codelineno-0-3)) -> int `

Processes a recording event.

#### WARNING

-   This function is deprecated here, and moved to [`general.processRECEvent()`](https://il-group.github.io/FL-Studio-API-Stubs/midi_controller_scripting/general/fl%20state/#general.__fl_state.processRECEvent) as of API version 7.

Included since API version 1.

Deprecated since API version 7.

