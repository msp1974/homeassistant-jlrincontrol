# JLR Home Assistant Integration (v1.0.0)
This repository contains a Home Assistant integration for the Jaguar Landrover InControl system, allowing visibility of key vehicle information and control of enabled services.

## Breaking Change in v1.0.0 From Previous Alpha Versions
Due to an issue in the unique ID being generated in the backend for the sensors, this fix causes HA to create new versions of these (all suffixed with _2).

In order to resolve this please follow the below when updating to v0.5alpha.
1) Comment out the integration in your config.yaml file.
2) Restart HA
3) In Configuration -> Entities, delete all the jlrincontrol entities.
4) Uncomment the integration in your config.yaml file.
5) Restart HA

Any cards you had setup for sensors in the UI and the HA name of these sensors will be the same as before.

# Functionality
Currently this loads a series of sensors for
* Vehicle Info
* Alarm
* Doors
* Windows
* Tyres
* Range
* Location
* EV Battery Sensor (EVs only)
* Service Info

And has services for
* Update Health Status (forces update from vehicle)
* Honk/Flash
* Lock/Unlock
* Start Engine/Stop Engine
* Start Charging/Stop Charging
* Reset Alarm
* Start Preconditioning/Stop Preconditioning
* Set Max Charge (Always and One Off)

**Note:** Not all services are available on all models and the error log will show this if not available on your vehicle.

**Note 2**: When calling a service, HA will monitor the status of the service call and report in the error log if it failed.  Debug log will show this checking and the success/failure reason.


As this is an alpha version, please be aware that updates could include breaking changes as we develop.

Also, due to lack of a fleet of Jaguars and LandRovers/RangeRovers (donations welcome!), there maybe issues with some models not supporting some funtions.  Please raise an issue for these and say what vehcile you have and post the log.

# Sample Images
![](https://raw.githubusercontent.com/msp1974/homeassistant-jlrincontrol/dev/docs/panel1.png)

## Additional Optional Parameters
1. scan_interval - in minutes. Default update interval is 5 minutes.  Use this to change that.  Minimum is 1 minute.
2. pin - set this to be able to use the lock/unlock on the lock sensor.
3. distance_unit - set this to 'mi' or 'km' to override the HA default metric for milages (mainly for funny UK system of miles and litres!).
4. health_update_interval - see health update section
5. debug_data: - see debugging below.

Required Parameters
```
jlrincontrol:
  username: <your InControl email address>
  password: <your InControl password>
```
Optional Parameters
```
  scan_interval: 5
  pin: <your InControl pin>
  distance_unit: <mi or km to override HA defualt>
  health_update_interval: 60
  debug_data: <false or true - see debugging>
```

# Health Status Update
New in v1.0.0

This integration now has the ability to perform a scheduled health status update request from your vehicle.  By default this is disabled.  Adding the entry to your configuration.yaml as above will enable it (after a HA restart).

I do not know the impact on either vehicle battery or JLRs view on running this often, so please use at your own risk.  I would certainly not set it to anything too often.

Alternatively, you can make a more intelligent health update request automation using the service call available in this integration and the output of some sensors.

I.e. on EV vehicles you could only call it if the vehicle is charging, or on all vehicles, only call it during the day and it was more than x period since the last update.

# Code Installation
The intention is to make this a HACS install when it has reached a decent level of functionality and stability.  For now please see manual installation instructions.

## Branch Versions
As of v1.0.0, the dev branch is now where the very latest version is held.  Please note that there maybe issues with new functions or fixes that have not been fully tested.  It will also be updated regularly as new fixes/functions are developed, so please check you have the latest update before raising an issue.  The master branch is the current release.

## Manual Code Installation
1. On your server clone the github repository into a suitable directory using the git clone command.<br>
`git clone https://github.com/msp1974/homeassistant-jlrincontrol.git`
2. Copy the jlrincontrol folder to the custom_components directory of your Home Assistant installation.
3. In your configuration.yaml file, add the following entry.


```
jlrincontrol:
  username: <your InControl email address>
  password: <your InControl password>
```

# Community Recipes
The [recipes](https://github.com/msp1974/homeassistant-jlrincontrol/blob/master/Recipes.md) page is a collection of ideas contributed by the community to help you get the most out of using this integration.

# Suggestions
I am looking for suggestions to improve this integration and make it useful for many people.  Please raise an issue for any functionality you would like to see.

# Contributors
This integration uses the jlrpy api written by [ardevd](https://github.com/ardevd/jlrpy).  A big thanks for all the work you have done on this.

# Debugging
1. To enable debug logging for this component, add the following to your configuration.yaml
```
logger:
  default: critical
  logs:
    custom_components.jlrincontrol: debug
```

2. To enable logging of the attributes and status data in the debug log, add the following to you configuration.yaml.
```
jlrincontrol:
  username: <your InControl email address>
  password: <your InControl password>
  debug_data: true
```


# Change Log

## v0.1alpha
Initial build of the component to read basic sensors

## v0.2alpha
* Updated to use jlrpy 1.3.3
* Added a bunch of new sensor information
* Better handles vehicles that do not present some sensor info

## v0.3alpha
* Fixed: Range sensor now handles EVs
* Added: New EV Charge sensor to show charge information (not fully tested)

## v0.4alpha
* Added: Improved debugging info to aid diagnosing differences in models

## v0.5alpha
* Added: Alarm sensor.
* Added: jlrincontrol services as listed in functionality to control vehicle.
* Added: Ability to schedule health status update - see health status section.
* Added: Ability to set the update interval fro the JLR servers.
* Updated: Use HA units to display data instead of relying on InControl user prefs as not reliable.
* Fixed: **BREAKING CHANGE** Issue with unique ID could cause duplicates.
* Fixed: Renamed last updated to last contact and displayed in local time.
* Fixed: Unlock/Lock on door sensor did not work. Need to add pin to configuration.yaml.  See additional parameters.
* Fixed: Device tracker not updating state.

## v1.0.0
* First official release - yeah!



### Known Issues
* Only works for first vehicle on account.
* Some distance sensors do not show in local units (on list to fix).
* Service Info sensor shows ok even if car is needing service or adblue top up (on list to fix)
* Tyre pressures seem to be in inconsistant units between models and therefore give strange reading.
* Tyre pressures are not in local units.


