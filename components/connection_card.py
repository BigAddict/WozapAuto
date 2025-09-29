from django_components import component


@component.register("connection_card")
class ConnectionCard(component.Component):
    template_name = "components/connection_card.html"
    
    def get_context_data(self, instance_name="Unknown Connection", connection_status="offline",
                        messages_count=0, last_activity=None, connection_id=None,
                        show_stats=True, show_actions=True, class_name=None, **kwargs):
        return {
            "instance_name": instance_name,
            "connection_status": connection_status,
            "messages_count": messages_count,
            "last_activity": last_activity,
            "connection_id": connection_id,
            "show_stats": show_stats,
            "show_actions": show_actions,
            "class_name": class_name,
        }
