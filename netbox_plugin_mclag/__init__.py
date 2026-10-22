from netbox.plugins import PluginConfig


class NetBoxMcLagConfig(PluginConfig):
    name = "netbox_plugin_mclag"
    verbose_name = "Multi-Chassis LAG"
    description = "Manage Multi-Chassis Link Aggregation Groups in Netbox (MC-LAG / MLAG / vPC / etc)"
    version = "0.2.3"
    base_url = "mclag"
    min_version = "4.6.0"
    max_version = "4.7.999"


config = NetBoxMcLagConfig
