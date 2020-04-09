# JLR Home Assistant Integration (v0.1alpha)
This reposiroty contains a Home Assistant integration for the Jaguar Landrover InControl system, allowing visibility of key vehicle information and control of enabled services.

# Functionality


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

v0.1alpha
Initial build of the component to read basic sensors