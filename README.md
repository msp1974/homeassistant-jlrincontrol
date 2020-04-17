# JLR Home Assistant Integration (v0.3alpha)
This repository contains a Home Assistant integration for the Jaguar Landrover InControl system, allowing visibility of key vehicle information and control of enabled services.

# Functionality
Currently this loads a series of sensors only.  I am in the process of adding services to control the vehicle.

As this is an alpha version, please be aware that updates could include breaking changes as we develop.

Also, due to lack of a fleet of Jaguars and LandRovers/RangeRovers (donations welcome!), there maybe issues with some models not supporting some funtions.  Please raise an issue for these and say what vehcile you have and post the log.

# Sample Images
![](https://raw.githubusercontent.com/msp1974/homeassistant-jlrincontrol/master/docs/panel1.png)

# Code Installation
The intention is to make this a HACS install when it has reached a decent level of functionality and stability.  For now please see manual installation instructions.

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

# Suggestions
I am looking for suggestions to improve this integration and make it useful for many people.  Please raise an issue for any functionality you would like to see.

# Contributors
This integration uses the jlrpy api written by [ardevd](https://github.com/ardevd/jlrpy).  A big thanks for all the work you have done on this.


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

### Known Issues
* Only works for first vehicle on account
* Some distance sensors do not show in local units
* Service Info sensor shows ok even if car is needing service or adblue top up


