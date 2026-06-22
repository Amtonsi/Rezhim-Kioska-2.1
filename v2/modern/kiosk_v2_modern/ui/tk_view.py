# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tkinter as tk
from tkinter import messagebox

from kiosk_v2_modern.ui.layout import LayoutTransform
from kiosk_v2_modern.ui.scene import DESIGN_HEIGHT, DESIGN_WIDTH, THEME, build_dialog_spec
from kiosk_v2_modern.ui.scene import build_operator_scene


def dialog_entry_options(masked=False):
    options = {
        "fg": THEME["text"],
        "bg": "#090b0f",
        "insertbackground": THEME["text"],
        "relief": "flat",
        "font": ("Consolas", 13),
        "highlightthickness": 1,
        "highlightbackground": "#4b5563",
        "highlightcolor": THEME["accent"],
        "selectbackground": THEME["accent"],
        "selectforeground": "#00111f",
    }
    if masked:
        options["show"] = "*"
    return options


class SceneRenderer(object):
    def __init__(self, canvas, action_handler, layout_class=LayoutTransform):
        self.canvas = canvas
        self.action_handler = action_handler
        self.layout_class = layout_class
        self._bound_actions = set()

    def render(self, scene, actual_width, actual_height):
        layout = self.layout_class(
            DESIGN_WIDTH,
            DESIGN_HEIGHT,
            actual_width,
            actual_height,
        )
        self.canvas.delete("all")
        for item in scene:
            self._draw_item(item, layout)
        return layout

    def _draw_item(self, item, layout):
        x, y, width, height = item["rect"]
        coordinates = layout.rectangle(x, y, x + width, y + height)
        kind = item["kind"]
        if kind == "background":
            self.canvas.create_rectangle(
                *coordinates,
                fill=item["fill"],
                outline=item["fill"],
                width=0,
            )
            return
        if kind == "rect":
            self._rounded_rectangle(
                coordinates,
                layout.font_size(item.get("radius", 0)),
                item["fill"],
                item.get("outline"),
            )
            return
        if kind == "text":
            self._draw_text(item, coordinates, layout)
            return
        if kind == "button":
            self._draw_button(item, coordinates, layout)
            return
        raise ValueError("Unknown scene item: {0}".format(kind))

    def _draw_text(self, item, coordinates, layout, tags=()):
        x1, y1, x2, y2 = coordinates
        anchor = item.get("anchor", "nw")
        if anchor == "center":
            position = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
        elif anchor == "ne":
            position = (x2, y1)
        else:
            position = (x1, y1)
        weight = "bold" if item.get("bold") else "normal"
        self.canvas.create_text(
            *position,
            text=item["text"],
            fill=item["fill"],
            anchor=anchor,
            width=max(1, int(round(x2 - x1))),
            font=(
                item.get("family", "Segoe UI"),
                -layout.font_size(item.get("size", 12)),
                weight,
            ),
            tags=tags,
        )

    def _draw_button(self, item, coordinates, layout):
        action = item["action"]
        tag = "action:{0}".format(action)
        self._rounded_rectangle(
            coordinates,
            layout.font_size(item.get("radius", 8)),
            item["fill"],
            item.get("outline"),
            (tag,),
        )
        text_item = dict(item)
        text_item["kind"] = "text"
        text_item["fill"] = item["textFill"]
        text_item["anchor"] = "center"
        self._draw_text(text_item, coordinates, layout, (tag,))
        if action not in self._bound_actions:
            self.canvas.tag_bind(
                tag,
                "<Button-1>",
                lambda _event, selected=action: self.action_handler(selected),
            )
            self._bound_actions.add(action)

    def _rounded_rectangle(self, coordinates, radius, fill, outline, tags=()):
        x1, y1, x2, y2 = coordinates
        radius = max(0, min(float(radius), (x2 - x1) / 2.0, (y2 - y1) / 2.0))
        if radius <= 0:
            return self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=fill,
                outline=outline or fill,
                width=1 if outline else 0,
                tags=tags,
            )
        points = (
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        )
        return self.canvas.create_polygon(
            *points,
            smooth=True,
            splinesteps=12,
            fill=fill,
            outline=outline or fill,
            width=1 if outline else 0,
            tags=tags,
        )


class LocalAdminDialog(object):
    def __init__(self, parent, on_submit, on_cancel, tk_module=tk):
        self.parent = parent
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.tk = tk_module
        self.window = tk_module.Toplevel(parent)
        self.username_entry = None
        self.password_entry = None
        self._build()

    def _build(self):
        spec = build_dialog_spec()
        window = self.window
        window.withdraw()
        window.title(spec["title"])
        window.configure(bg=THEME["panel2"])
        window.resizable(False, False)
        window.transient(self.parent)
        window.protocol("WM_DELETE_WINDOW", self.cancel)
        window.attributes("-topmost", True)

        self.tk.Label(
            window,
            text=spec["title"],
            fg=THEME["text"],
            bg=THEME["panel2"],
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        ).place(x=30, y=24, width=370, height=34)
        self.tk.Label(
            window,
            text=spec["message"],
            fg=THEME["muted"],
            bg=THEME["panel2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).place(x=30, y=62, width=370, height=34)

        self.username_entry = self._entry(spec["fields"][0], 112, False)
        self.password_entry = self._entry(spec["fields"][1], 184, True)

        self.tk.Button(
            window,
            text=spec["acceptText"],
            command=self.submit,
            bg=THEME["blue"],
            fg="#00111f",
            activebackground=THEME["accent"],
            activeforeground="#00111f",
            relief="flat",
            font=("Segoe UI", 11, "bold"),
        ).place(x=176, y=262, width=105, height=40)
        self.tk.Button(
            window,
            text=spec["cancelText"],
            command=self.cancel,
            bg="#242a31",
            fg=THEME["text"],
            activebackground="#303740",
            activeforeground=THEME["text"],
            relief="flat",
            font=("Segoe UI", 11),
        ).place(x=295, y=262, width=105, height=40)

        window.bind("<Return>", lambda _event: self.submit())
        window.bind("<Escape>", lambda _event: self.cancel())
        self._center(430, 330)
        window.deiconify()
        window.lift()
        window.grab_set()
        window.after_idle(self._focus_username)

    def _entry(self, field, y, masked):
        self.tk.Label(
            self.window,
            text=field["label"],
            fg=THEME["muted"],
            bg=THEME["panel2"],
            font=("Segoe UI", 10),
            anchor="w",
        ).place(x=30, y=y, width=370, height=20)
        entry = self.tk.Entry(self.window, **dialog_entry_options(masked))
        entry.place(x=30, y=y + 24, width=370, height=38)
        return entry

    def _center(self, width, height):
        self.parent.update_idletasks()
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        left = max(0, int((screen_width - width) / 2))
        top = max(0, int((screen_height - height) / 2))
        self.window.geometry("{0}x{1}+{2}+{3}".format(width, height, left, top))

    def _focus_username(self):
        self.window.focus_force()
        self.username_entry.focus_set()

    def submit(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        self.password_entry.delete(0, self.tk.END)
        self.close()
        try:
            self.on_submit(username, password)
        finally:
            password = None

    def cancel(self):
        self.password_entry.delete(0, self.tk.END)
        self.close()
        self.on_cancel()

    def close(self):
        try:
            self.window.grab_release()
        except self.tk.TclError:
            pass
        self.window.destroy()


class KioskCanvasView(object):
    def __init__(
        self,
        root,
        model_provider,
        action_handler,
        auth_submit,
        auth_cancel,
        shell_interaction=None,
        tk_module=tk,
    ):
        self.root = root
        self.model_provider = model_provider
        self.action_handler = action_handler
        self.auth_submit = auth_submit
        self.auth_cancel = auth_cancel
        self.shell_interaction = shell_interaction or (lambda: None)
        self.tk = tk_module
        self.admin_session_active = False
        self.dialog = None
        self.auth_error_message = (
            "Отказано в доступе. Неверное имя пользователя или пароль."
        )
        self.restore_error_message = "Восстановление Windows не выполнено."
        root.configure(bg=THEME["background"])
        root.title("Режим киоска")
        root.attributes("-fullscreen", True)
        root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.canvas = tk_module.Canvas(
            root,
            bg=THEME["background"],
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk_module.BOTH, expand=True)
        self.renderer = SceneRenderer(self.canvas, self._dispatch)
        self.canvas.bind("<Button-1>", self._on_shell_click, add="+")
        root.bind("<Configure>", self._on_resize)

    def show_operator(self):
        self.admin_session_active = False
        self.refresh()

    def show_admin_session(self):
        self.admin_session_active = True
        self.refresh()

    def show_admin_dialog(self):
        if self.dialog is not None:
            self.dialog.window.lift()
            self.dialog.window.focus_force()
            return
        self.dialog = LocalAdminDialog(
            self.root,
            self._submit_credentials,
            self._cancel_authentication,
            self.tk,
        )

    def show_auth_error(self):
        messagebox.showerror(
            "Режим киоска",
            self.auth_error_message,
            parent=self.root,
        )

    def set_auth_error(self, message):
        self.auth_error_message = message

    def show_restore_error(self):
        messagebox.showerror(
            "Режим киоска",
            self.restore_error_message,
            parent=self.root,
        )

    def set_restore_error(self, message):
        self.restore_error_message = message

    def show_restore_result(self):
        messagebox.showinfo(
            "Режим киоска",
            "Восстановление завершено.",
            parent=self.root,
        )

    def refresh(self):
        model = dict(self.model_provider() or {})
        scene = build_operator_scene(
            model.get("application_path", ""),
            app_status=model.get("app_status", "running"),
            application_configured=model.get("application_configured", True),
            admin_session_active=self.admin_session_active,
            supervision_enabled=model.get("supervision_enabled", True),
            isolation_degraded=model.get("isolation_degraded", False),
        )
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        self.renderer.render(scene, width, height)

    def _on_resize(self, _event):
        self.refresh()

    def _dispatch(self, action):
        self.action_handler(action)

    def _on_shell_click(self, _event):
        if self._current_item_is_action():
            return
        self.root.after(0, self.shell_interaction)

    def _current_item_is_action(self):
        canvas = getattr(self, "canvas", None)
        if canvas is None:
            return False
        try:
            current = canvas.find_withtag("current")
            if not current:
                return False
            tags = canvas.gettags(current[0])
        except Exception:
            return False
        return any(str(tag).startswith("action:") for tag in tags)

    def _submit_credentials(self, username, password):
        self.dialog = None
        self.auth_submit(username, password)

    def _cancel_authentication(self):
        self.dialog = None
        self.auth_cancel()
