import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, Gio, GdkPixbuf
import numpy as np
from PIL import Image
from scipy.ndimage import sobel, gaussian_filter
import os

class UpscaleApp(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(1280, 720)
        self.set_title("Image Upscaler")

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(main_box)

        # Header bar
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu = Gio.Menu()
        menu.append("Quit", "app.quit")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Control box
        control_box = Gtk.Box(spacing=6)
        main_box.append(control_box)

        # Load button
        load_button = Gtk.Button(label="Load Image")
        load_button.connect("clicked", self.on_load)
        control_box.append(load_button)

        # Export button
        export_button = Gtk.Button(label="Export Image")
        export_button.connect("clicked", self.on_export)
        control_box.append(export_button)

        # Upscale multiplier
        multiplier_label = Gtk.Label(label="Upscale Multiplier:")
        control_box.append(multiplier_label)
        self.multiplier_spin = Gtk.SpinButton()
        self.multiplier_spin.set_range(1, 16)
        self.multiplier_spin.set_value(8)
        control_box.append(self.multiplier_spin)

        # Mask detail level
        detail_label = Gtk.Label(label="Mask Detail Level:")
        control_box.append(detail_label)
        self.detail_spin = Gtk.SpinButton()
        self.detail_spin.set_range(0.1, 1.0)
        self.detail_spin.set_value(0.1)
        self.detail_spin.set_increments(0.1, 0.1)
        control_box.append(self.detail_spin)

        # Smoothing threshold
        smooth_label = Gtk.Label(label="Smoothing Threshold (%):")
        control_box.append(smooth_label)
        self.smooth_threshold_spin = Gtk.SpinButton()
        self.smooth_threshold_spin.set_range(0, 100)
        self.smooth_threshold_spin.set_value(85)
        self.smooth_threshold_spin.set_increments(5, 5)
        control_box.append(self.smooth_threshold_spin)

        # Preview box (full width)
        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preview_box.set_hexpand(True)
        main_box.append(preview_box)

        # Original preview (expanded)
        orig_frame = Gtk.Frame(label="Original")
        orig_frame.set_hexpand(True)
        orig_frame.set_vexpand(True)
        self.orig_image = Gtk.Image()
        orig_frame.set_child(self.orig_image)
        preview_box.append(orig_frame)

        # Upscaled preview (expanded)
        upscaled_frame = Gtk.Frame(label="Upscaled")
        upscaled_frame.set_hexpand(True)
        upscaled_frame.set_vexpand(True)
        self.upscaled_image = Gtk.Image()
        upscaled_frame.set_child(self.upscaled_image)
        preview_box.append(upscaled_frame)

        # View percentage adjustments
        view_box = Gtk.Box(spacing=6)
        main_box.append(view_box)

        orig_view_label = Gtk.Label(label="Original View %:")
        view_box.append(orig_view_label)
        self.orig_view_spin = Gtk.SpinButton()
        self.orig_view_spin.set_range(10, 100)
        self.orig_view_spin.set_value(50)
        self.orig_view_spin.connect("value-changed", self.update_previews)
        view_box.append(self.orig_view_spin)

        upscaled_view_label = Gtk.Label(label="Upscaled View %:")
        view_box.append(upscaled_view_label)
        self.upscaled_view_spin = Gtk.SpinButton()
        self.upscaled_view_spin.set_range(10, 100)
        self.upscaled_view_spin.set_value(50)
        self.upscaled_view_spin.connect("value-changed", self.update_previews)
        view_box.append(self.upscaled_view_spin)

        self.original_img = None
        self.upscaled_img = None

    def on_load(self, button):
        dialog = Gtk.FileDialog()
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        filter = Gtk.FileFilter()
        filter.set_name("Image files")
        filter.add_mime_type("image/jpeg")
        filter.add_mime_type("image/png")
        filters.append(filter)
        dialog.set_filters(filters)
        dialog.open(self, None, self.on_load_response)

    def on_load_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.original_img = Image.open(file.get_path()).convert('RGB')
                self.update_previews()
        except Exception as e:
            print(f"Error loading file: {e}")

    def on_export(self, button):
        if self.upscaled_img:
            dialog = Gtk.FileDialog()
            filters = Gio.ListStore(item_type=Gtk.FileFilter)
            filter = Gtk.FileFilter()
            filter.set_name("JPEG files")
            filter.add_mime_type("image/jpeg")
            filters.append(filter)
            dialog.set_filters(filters)
            initial_file = Gio.File.new_for_path("upscaled.jpg")
            dialog.set_initial_file(initial_file)
            dialog.save(self, None, self.on_export_response)

    def on_export_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                # Ensure full upscaled image is saved, not resized version
                full_upscaled_img = self.upscaled_img
                full_upscaled_img.save(file.get_path())
        except Exception as e:
            print(f"Error saving file: {e}")

    def create_edge_mask(self, img_array, threshold):
        img_array = np.array(img_array.convert('L'), dtype=np.float32) / 255.0
        edges = sobel(img_array)
        # Threshold to determine uniform areas (inverted logic)
        uniform_threshold = threshold
        mask = (edges <= uniform_threshold).astype(np.uint8)
        return mask

    def upscale_mask(self, mask, scale_factor):
        height, width = mask.shape
        return np.repeat(np.repeat(mask, scale_factor, axis=0), scale_factor, axis=1)

    def fill_upscaled_image(self, orig_array, upscaled_mask):
        scale_factor = self.multiplier_spin.get_value_as_int()
        new_height, new_width = orig_array.shape[0] * scale_factor, orig_array.shape[1] * scale_factor
        upscaled_orig = np.repeat(np.repeat(orig_array, scale_factor, axis=0), scale_factor, axis=1)
        
        # Apply Gaussian blur to uniform areas based on smoothing threshold
        smoothing_threshold = self.smooth_threshold_spin.get_value_as_int() / 100.0
        result = upscaled_orig.copy()
        for channel in range(3):  # RGB channels
            channel_data = result[:, :, channel]
            # Apply blur only where mask is strong (above smoothing threshold)
            blurred_channel = gaussian_filter(channel_data * (upscaled_mask > smoothing_threshold), sigma=1.0)
            result[:, :, channel] = np.where(upscaled_mask > smoothing_threshold, blurred_channel, channel_data)
        
        return result

    def update_previews(self, widget=None):
        if self.original_img:
            # Original preview
            orig_percent = self.orig_view_spin.get_value_as_int() / 100
            orig_size = (int(self.original_img.width * orig_percent), int(self.original_img.height * orig_percent))
            orig_preview = self.original_img.resize(orig_size, Image.Resampling.NEAREST)
            data = orig_preview.tobytes()
            loader = GdkPixbuf.Pixbuf.new_from_data(
                data,
                GdkPixbuf.Colorspace.RGB,
                False,
                8,
                orig_preview.size[0],
                orig_preview.size[1],
                orig_preview.size[0] * 3
            )
            texture = Gdk.Texture.new_for_pixbuf(loader)
            self.orig_image.set_from_paintable(texture)

            # Upscaled preview
            mask = self.create_edge_mask(self.original_img, self.detail_spin.get_value())
            upscaled_mask = self.upscale_mask(mask, self.multiplier_spin.get_value_as_int())
            orig_array = np.array(self.original_img)
            self.upscaled_img = Image.fromarray(self.fill_upscaled_image(orig_array, upscaled_mask))
            upscaled_percent = self.upscaled_view_spin.get_value_as_int() / 100
            upscaled_size = (int(self.upscaled_img.width * upscaled_percent), int(self.upscaled_img.height * upscaled_percent))
            upscaled_preview = self.upscaled_img.resize(upscaled_size, Image.Resampling.NEAREST)
            data = upscaled_preview.tobytes()
            loader = GdkPixbuf.Pixbuf.new_from_data(
                data,
                GdkPixbuf.Colorspace.RGB,
                False,
                8,
                upscaled_preview.size[0],
                upscaled_preview.size[1],
                upscaled_preview.size[0] * 3
            )
            texture = Gdk.Texture.new_for_pixbuf(loader)
            self.upscaled_image.set_from_paintable(texture)

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.example.upscale")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        window = UpscaleApp(application=app)
        window.present()

if __name__ == "__main__":
    app = Application()
    app.run()