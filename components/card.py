from django_components import component


@component.register("card")
class Card(component.Component):
    template_name = "components/card.html"
    
    def get_context_data(self, title=None, subtitle=None, header=None, text=None, 
                        footer=None, hover_lift=False, glassmorphism=False, 
                        variant="default", class_name=None, **kwargs):
        return {
            "title": title,
            "subtitle": subtitle,
            "header": header,
            "text": text,
            "footer": footer,
            "hover_lift": hover_lift,
            "glassmorphism": glassmorphism,
            "variant": variant,
            "class_name": class_name,
        }
