# JLR InControl Recipes

This page documents some Home Assistant recipes to help get the most out of this integration.

Please feel free to submit your own for inclusion into this page.

## Lovelace UI

### **_Create a button to request the vehicle to update_**

Add a button to your UI and set the configuration to call the jlr_incontrol.update_health_status service.

```yaml
entity: sensor.my_car_info
hold_action:
  action: more-info
name: Update My Car
show_icon: true
show_name: true
tap_action:
  action: call-service
  service: jlrincontrol.update_health_status
  service_data:
    entity_id: sensor.my_car_info
type: button
```

### **_Create a stack of buttons to control pin required services as per the readme image._**

```yaml
cards:
  - cards:
      - entity: lock.my_car_doors
        hold_action:
          action: more-info
        icon: 'mdi:car-door-lock'
        name: Lock Doors
        show_icon: true
        show_name: true
        tap_action:
          action: call-service
          service: jlrincontrol.lock_vehicle
          service_data:
            entity_id: sensor.my_car_info
            pin: XXXX
        type: button
      - entity: lock.my_car_doors
        hold_action:
          action: more-info
        icon: 'mdi:car-door'
        name: Unlock Doors
        show_icon: true
        show_name: true
        tap_action:
          action: call-service
          service: jlrincontrol.unlock_vehicle
          service_data:
            entity_id: sensor.my_car_info
            pin: XXXX
        type: button
    type: horizontal-stack
  - cards:
      - entity: sensor.my_car_info
        hold_action:
          action: more-info
        name: Start Engine
        show_icon: true
        show_name: true
        tap_action:
          action: call-service
          service: jlrincontrol.start_vehicle
          service_data:
            entity_id: sensor.my_car_info
            pin: XXXX
            target_value: 43
        type: button
      - entity: sensor.my_car_info
        hold_action:
          action: more-info
        icon: 'mdi:car-off'
        name: Stop Engine
        show_icon: true
        show_name: true
        tap_action:
          action: call-service
          service: jlrincontrol.stop_vehicle
          service_data:
            entity_id: sensor.my_car_info
            pin: XXXX
        type: button
    type: horizontal-stack
type: vertical-stack
```

## Super Cool Lovelace Card

Create a nice looking lovelace card with sensor information.

![](https://raw.githubusercontent.com/msp1974/homeassistant-jlrincontrol/master/docs/lovelace-picture-card.png)

This card will require the following mods:

- https://github.com/thomasloven/lovelace-card-mod

which can be installed via HACS.

Example code below used to create this card.

```yaml
type: picture-elements
image: /local/ipace.png
style: |
  #root > hui-image {
    display: block;
    width: 80%;
    top: 10px;
    padding: 0px 0px 30px 0px;
    margin: auto;
  }
elements:
  - type: image
    image: /local/cardbackK.png
    style:
      left: 50%
      top: 90%
      width: 100%
      height: 60px
  - type: state-icon
    entity: lock.my_car_doors
    tap_action: more_info
    style:
      color: white
      left: 10%
      top: 86%
  - type: state-label
    entity: lock.my_car_doors
    style:
      color: white
      left: 10%
      top: 95%
  - type: state-icon
    entity: sensor.my_car_windows
    tap_action: more_info
    style:
      color: white
      left: 30%
      top: 86%
  - type: state-label
    entity: sensor.my_car_windows
    style:
      color: white
      left: 30%
      top: 95%
  - type: icon
    icon: 'mdi:security'
    entity: sensor.my_car_alarm
    tap_action: more_info
    style:
      color: white
      left: 50%
      top: 86%
  - type: state-label
    entity: sensor.my_car_alarm
    style:
      color: white
      left: 50%
      top: 95%
  - type: state-icon
    entity: sensor.my_car_range
    tap_action: more_info
    style:
      color: white
      left: 70%
      top: 86%
  - type: state-label
    entity: sensor.my_car_range
    style:
      color: white
      left: 70%
      top: 95%
  - type: state-icon
    entity: sensor.my_car_info
    tap_action: more_info
    style:
      color: white
      left: 90%
      top: 86%
  - type: state-label
    entity: sensor.my_car_info
    attribute: Distance To Service
    style:
      color: white
      left: 90%
      top: 95%
```

## Custom template sensors

The `All info` sensor has a rich list of data attributes. You can easily use these attributes as source to new sensors
by using the [Template integration](https://www.home-assistant.io/integrations/template/).

### Battery template sensor

```yaml
template:
  - sensor:
      - name: "My Car Battery Sensor"
        icon: "mdi:car-battery"
        state: "{{ state_attr('sensor.my_car_all_info','core status').batteryVoltage }}"
        attributes:
          battery_status: "{{ state_attr('sensor.my_car_all_info','core status').batteryStatus }}"
          tu_status: "{{ state_attr('sensor.my_car_all_info','core status').tuStatusPower }}"
          tu_serial: "{{ state_attr('sensor.my_car_all_info','attributes').telematicsDevice.serialNumber }}"
```

### Battery template sensor - legacy format

Same example in legacy format (deprecated -
see [here](https://www.home-assistant.io/integrations/template/#legacy-sensor-configuration-format))

```yaml
sensor:
  - platform: template
    sensors:
      example_json_sensor:
        friendly_name: "My Car Battery Sensor"
        icon_template: "mdi:car-battery"
        value_template: "{{ state_attr('sensor.my_car_all_info','core status').batteryVoltage }}"
        attribute_templates:
          battery_status: "{{ state_attr('sensor.my_car_all_info','core status').batteryStatus }}"
          tu_status: "{{ state_attr('sensor.my_car_all_info','core status').tuStatusPower }}"
          tu_serial: "{{ state_attr('sensor.my_car_all_info','attributes').telematicsDevice.serialNumber }}"
```

### Precondition status and remaining time sensor
This recipe creates two sensors, remaining time of precondition (in minutes) and preconditioning status (on/of)

![](docs/preconditioning-off.png) ![](docs/preconditioning-on.png)

**Caveat**

- I choose to use `binary_sensor` (`on`/`off`) for precondition status, but the status actually got 3 states:
  1) `PRECLIM` (on), `OFF` and `STARTUP` (starting). I did not bother to reflect all three states, but only on/off
- the remaining runtime minutes is updated according to the `scan interval` (default to `5 minutes`, can be changed in the
  integration Configuration, but not sure about the side effect of increasing this update)

```yaml
template:
  - sensor:
      - unique_id: my_car_precondition_remaining_runtime_minutes
        device_class: duration
        unit_of_measurement: min
        attributes:
          friendly_name: "Precondition Remaining Runtime Minutes"
        # we need to handle that remaining runtime minutes is not reset if precondition is manually switched off
        state: >-
          {% set evStatus = state_attr('sensor.my_car_all_info', 'ev status') %}

          {% if is_state('binary_sensor.template_my_car_precondition_operating_status', 'on') and evStatus != None and evStatus != 'unknown' %}
            {{ evStatus.evPreconditionRemainingRuntimeMinutes | int }}
          {% else %}
            0
          {% endif %}
  - binary_sensor:
      - unique_id: my_car_precondition_operating_status
        device_class: running
        attributes:
          friendly_name: "Precondition Operating Status"
        state: >-
          {% set evStatus = state_attr('sensor.my_car_all_info', 'ev status') %}

          {% if evStatus == None or evStatus == 'unknown' %}
            off
          {% elif evStatus.evPreconditionOperatingStatus == 'OFF' %}
            off
          {% else %}
            on
          {% endif %}
        icon: >-
          {% set evStatus = state_attr('sensor.my_car_all_info', 'ev status') %}

          {% if evStatus == None or evStatus == 'unknown' %}
            mdi:fan-alert
          {% elif evStatus.evPreconditionOperatingStatus == 'OFF' %}
            mdi:fan-off
          {% else %}
            mdi:fan
          {% endif %}
```
