# JLR InControl Recipes
This page documents some Home Assistant recipes to help get the most out of this integration.

Please feel free to submit your own for inclusion into this page.

## Lovelace UI
### ***Create a button to request the vehicle to update***

Add a button to your UI and set the configuration to call the jlr_incontrol.update_health_status service.
```
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