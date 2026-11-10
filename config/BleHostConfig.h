#pragma once
// This project builds NimBLE-Arduino from source, but uses a prebuilt controller.
// Include the SDK defaults FIRST so later SDK includes cannot restore them.
// Only host-side values change here; controller buffers/ABI and task stacks stay intact.
#include <sdkconfig.h>
#define CROSSMOSA_BLE_HOST_CONFIG 1
#undef CONFIG_BT_NIMBLE_MAX_CONNECTIONS
#define CONFIG_BT_NIMBLE_MAX_CONNECTIONS 1
#undef CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU
#define CONFIG_BT_NIMBLE_ATT_PREFERRED_MTU 23
#undef CONFIG_NIMBLE_ROLE_PERIPHERAL
#undef CONFIG_BT_NIMBLE_ROLE_PERIPHERAL
#define CONFIG_BT_NIMBLE_ROLE_PERIPHERAL 0
#undef CONFIG_NIMBLE_ROLE_BROADCASTER
#undef CONFIG_BT_NIMBLE_ROLE_BROADCASTER
#define CONFIG_BT_NIMBLE_ROLE_BROADCASTER 0
// Keep block sizes, reducing counts for one small-report HID connection.
#undef CONFIG_BT_NIMBLE_MSYS_1_BLOCK_COUNT
#define CONFIG_BT_NIMBLE_MSYS_1_BLOCK_COUNT 4
#undef CONFIG_BT_NIMBLE_MSYS_2_BLOCK_COUNT
#define CONFIG_BT_NIMBLE_MSYS_2_BLOCK_COUNT 4
