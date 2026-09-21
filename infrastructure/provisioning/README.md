# Provisioning

Provisioning is intentionally device-specific. A production image must create a non-root runtime user, restrict camera and recording permissions, generate or securely import the device identity, and keep model caches and recordings on separate persistent volumes.
