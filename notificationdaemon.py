from typing import cast
from fabric import Application
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.image import Image
from fabric.widgets.button import Button
from fabric.widgets.wayland import WaylandWindow
from fabric.notifications import Notifications, Notification
from fabric.utils import invoke_repeater, get_relative_path
from playsound import playsound
from gi.repository import GdkPixbuf
import os
import threading


NOTIFICATION_WIDTH = 360
NOTIFICATION_IMAGE_SIZE = 64


class NotificationWidget(Box):
    def __init__(self, notification: Notification, **kwargs):
        super().__init__(
            size=(NOTIFICATION_WIDTH, -1),
            name="notification",
            spacing=8,
            orientation="v",
            **kwargs,
        )

        self._notification = notification

        body_container = Box(spacing=4, orientation="h")

        if image_pixbuf := self._notification.image_pixbuf:
            body_container.add(
                Image(
                    pixbuf=image_pixbuf.scale_simple(
                        NOTIFICATION_IMAGE_SIZE,
                        NOTIFICATION_IMAGE_SIZE,
                        GdkPixbuf.InterpType.BILINEAR,
                    )
                )
            )

        if app_icon := self._notification.app_icon:
            if os.path.exists(app_icon):
                body_container.add(
                    Image(
                        image_file=app_icon,
                        size=NOTIFICATION_IMAGE_SIZE
                    )
                )
            else:
                body_container.add(
                    Image(
                        icon_name=app_icon,
                        size=NOTIFICATION_IMAGE_SIZE
                    )
                )

        body_container.add(
            Box(
                spacing=4,
                orientation="v",
                children=[
                    # a box for holding both the "summary" label and the "close" button
                    Box(
                        orientation="h",
                        children=[
                            Label(
                                label=self._notification.summary,
                                ellipsization="middle",
                            )
                            .build()
                            .add_style_class("summary")
                            .unwrap(),
                        ],
                        h_expand=True,
                        v_expand=True,
                    )
                    # add the "close" button
                    .build(
                        lambda box, _: box.pack_end(
                            Button(
                                image=Image(
                                    icon_name="window-close",
                                    icon_size=14,
                                ),
                                v_align="center",
                                h_align="end",
                                on_clicked=lambda *_: self._notification.close(),
                            ),
                            False,
                            False,
                            0,
                        )
                    ),
                    Label(
                        label=self._notification.body,
                        line_wrap="word-char",
                        v_align="start",
                        h_align="start",
                    )
                    .build()
                    .add_style_class("body")
                    .unwrap(),
                ],
                h_expand=True,
                v_expand=True,
            )
        )

        self.add(body_container)

        if actions := self._notification.actions:
            self.add(
                Box(
                    spacing=4,
                    orientation="h",
                    children=[
                        Button(
                            h_expand=True,
                            v_expand=True,
                            label=action.label,
                            on_clicked=lambda *_, action=action: action.invoke(),
                        )
                        for action in actions
                    ],
                )
            )

        # destroy this widget once the notification is closed
        self._notification.connect(
            "closed",
            lambda *_: (
                parent.remove(self) if (parent := self.get_parent()) else None,  # type: ignore
                self.destroy(),
            ),
        )

        # automatically close the notification after the timeout period
        invoke_repeater(
            self._notification.timeout if self._notification.timeout > 0 else 3000,
            lambda: self._notification.close("expired"),
            initial_call=False,
        )


def play_click():
    playsound("/usr/share/sounds/gnome/default/alerts/click.ogg")


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)

    app = Application(
        "notifications",
        WaylandWindow(
            margin="8px 8px 8px 8px",
            anchor="top right",
            child=Box(
                size=2,  # so it's not ignored by the compositor
                spacing=4,
                orientation="v",
            ).build(
                lambda viewport, _: Notifications(
                    on_notification_added=lambda notifs_service, nid: (
                        threading.Thread(target=play_click, daemon=True).start(),
                        viewport.add(
                            NotificationWidget(
                                cast(
                                    Notification,
                                    notifs_service.get_notification_from_id(nid),
                                )
                            )
                        )
                    )
                )
            ),
            visible=True,
            all_visible=True,
        ),
    )

    app.set_stylesheet_from_file(get_relative_path("./style.css"))

    app.run()