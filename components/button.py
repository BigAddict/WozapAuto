from django_components import component


@component.register("button")
class Button(component.Component):
    template_name = "components/button.html"
    
    def get_context_data(self, type="button", variant="primary", size="md", outline=False, 
                        whatsapp_style=False, loading=False, disabled=False, name=None, 
                        id=None, onclick=None, icon=None, content=None, label=None, 
                        badge=None, class_name=None, **kwargs):
        return {
            "type": type,
            "variant": variant,
            "size": size,
            "outline": outline,
            "whatsapp_style": whatsapp_style,
            "loading": loading,
            "disabled": disabled or loading,
            "name": name,
            "id": id,
            "onclick": onclick,
            "icon": icon,
            "content": content or label or "Button",
            "badge": badge,
            "class_name": class_name,
        }
