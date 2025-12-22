from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Style:
    color: str | None = None
    bg: str | None = None

    font_weight: str | None = None
    font_size: str | None = None
    text_decoration: str | None = None
    text_align: str | None = None
    opacity: float | None = None

    w: int | str | None = None
    h: int | str | None = None

    p: int | None = None
    px: int | None = None
    py: int | None = None
    pt: int | None = None
    pb: int | None = None
    pl: int | None = None
    pr: int | None = None

    m: int | None = None
    mt: int | None = None
    mb: int | None = None
    ml: int | None = None
    mr: int | None = None

    flex_grow: float | None = None
    flex_shrink: float | None = None
    align: str | None = None
    justify: str | None = None
    gap: int | float | None = None
    direction: str | None = None

    overflow: str | None = None

    border: bool = False
    border_right: bool = False
    border_top: bool = False
    border_bottom: bool = False
    border_left: bool = False
    border_color: str | None = None
    rounded: str | None = None

    shadow: str | None = None

    w_full: bool = False

    hover: Style | None = None

    def __or__(self, other: Style | None) -> Style:
        if other is None:
            return self

        from dataclasses import fields, replace

        merged_kwargs: dict[str, object] = {}
        for field in fields(self):
            if field.name == "hover":
                merged_kwargs["hover"] = other.hover if other.hover is not None else self.hover
            else:
                self_val = getattr(self, field.name)
                other_val = getattr(other, field.name)

                if isinstance(other_val, bool):
                    merged_kwargs[field.name] = other_val if other_val else self_val
                else:
                    merged_kwargs[field.name] = other_val if other_val is not None else self_val

        return replace(self, **merged_kwargs)
