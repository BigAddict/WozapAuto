from django_components import component


@component.register("form_field")
class FormField(component.Component):
    template_name = "components/form_field.html"
    
    def get_context_data(self, name, label=None, type="text", value=None, placeholder=None,
                        required=False, disabled=False, help_text=None, error_message=None,
                        is_invalid=False, is_valid=False, class_name=None, id=None,
                        rows=None, cols=None, min=None, max=None, step=None, pattern=None,
                        options=None, **kwargs):
        return {
            "name": name,
            "label": label,
            "type": type,
            "value": value,
            "placeholder": placeholder,
            "required": required,
            "disabled": disabled,
            "help_text": help_text,
            "error_message": error_message,
            "is_invalid": is_invalid,
            "is_valid": is_valid,
            "class_name": class_name,
            "id": id or name,
            "rows": rows,
            "cols": cols,
            "min": min,
            "max": max,
            "step": step,
            "pattern": pattern,
            "options": options,
        }
