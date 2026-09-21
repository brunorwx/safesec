# Notifications

`AlertService` accepts transport-specific sinks through `NotificationSink`. Delivery is local and transport-neutral at this layer; remote channels should be added only after authentication and retry semantics are defined in the gateway phase.
