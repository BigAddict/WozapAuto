from django_components import component


@component.register("stat_card")
class StatCard(component.Component):
    template_name = "components/stat_card.html"
    
    def get_context_data(self, title="Statistic", value="0", change=None, icon=None, 
                        color="primary", class_name=None, **kwargs):
        return {
            "title": title,
            "value": value,
            "change": change,
            "icon": icon,
            "color": color,
            "class_name": class_name,
        }
