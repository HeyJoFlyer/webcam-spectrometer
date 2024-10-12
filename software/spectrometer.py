import cv2
import tkinter as tk
from tkinter import Label, Toplevel, simpledialog, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
import json
import os

class SpectrumAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spectrum Analyzer with Selectable ROI")

        # Capture video from webcam
        self.cap = cv2.VideoCapture(4)

        # Create a label to display the frames
        self.label = Label(root)
        self.label.pack()

        # Variables for ROI selection
        self.roi_start_x = None
        self.roi_start_y = None
        self.roi_end_x = None
        self.roi_end_y = None
        self.selecting_roi = False  # Flag for whether the ROI is being selected

        # Calibration data
        self.start_wavelength = None
        self.end_wavelength = None
        self.pixel_to_wavelength = None  # Array to store pixel-to-wavelength mapping

        # ROI display window (Toplevel)
        self.roi_window = None
        self.roi_label = None

        # Setup matplotlib for live updating
        plt.ion()  # Enable interactive mode for real-time updating
        self.fig, self.ax = plt.subplots()  # Create the figure and axis for the plot
        self.line, = self.ax.plot([], [])  # Initialize the plot with an empty line

        # Add a menu for saving/reloading the spectrum
        self.create_menu()

        # Bind mouse events for ROI selection
        self.label.bind("<ButtonPress-1>", self.on_mouse_down)  # Left-click to start ROI
        self.label.bind("<B1-Motion>", self.on_mouse_drag)       # Dragging the mouse
        self.label.bind("<ButtonRelease-1>", self.on_mouse_up)   # Release to finalize ROI

        # Update the frame every 10 ms
        self.update_frame()

    def create_menu(self):
        """Create a menu for saving and reloading spectra."""
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Save Spectrum", command=self.save_spectrum)
        filemenu.add_command(label="Reload Spectrum", command=self.reload_spectrum)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def on_mouse_down(self, event):
        """Callback when the mouse button is pressed down, starting the ROI selection."""
        self.roi_start_x = event.x
        self.roi_start_y = event.y
        self.selecting_roi = True

        # Close the previous ROI window if any
        if self.roi_window:
            self.roi_window.destroy()
            self.roi_window = None

    def on_mouse_drag(self, event):
        """Callback when the mouse is dragged, updating the rectangle dynamically."""
        if self.selecting_roi:
            self.roi_end_x = event.x
            self.roi_end_y = event.y

    def on_mouse_up(self, event):
        """Callback when the mouse button is released, finalizing the ROI."""
        self.selecting_roi = False
        if self.roi_start_x and self.roi_start_y and self.roi_end_x and self.roi_end_y:
            # Create a new window to display the ROI
            self.show_roi_window()
            # After selecting the ROI, prompt the user for wavelength calibration
            self.calibrate_wavelengths()

    def show_roi_window(self):
        """Create a separate window to display the selected ROI."""
        if not self.roi_window:
            self.roi_window = Toplevel(self.root)
            self.roi_window.title("Selected Spectrum ROI")
            self.roi_label = Label(self.roi_window)
            self.roi_label.pack()

    def update_roi_window(self, roi_frame):
        """Update the ROI window with the selected region."""
        if self.roi_label:
            # Convert the ROI frame to an image that can be displayed in Tkinter
            roi_img = Image.fromarray(roi_frame)
            roi_imgtk = ImageTk.PhotoImage(image=roi_img)

            # Update the ROI label
            self.roi_label.imgtk = roi_imgtk
            self.roi_label.configure(image=roi_imgtk)

    def calibrate_wavelengths(self):
        """Prompt the user to enter the start and end wavelengths for calibration."""
        # Get the calibration input from the user
        self.start_wavelength = float(simpledialog.askstring("Calibration", "Enter the start wavelength (e.g., 400 nm):"))
        self.end_wavelength = float(simpledialog.askstring("Calibration", "Enter the end wavelength (e.g., 700 nm):"))

        # Calculate pixel-to-wavelength mapping
        if self.roi_start_x and self.roi_end_x:
            num_pixels = self.roi_end_x - self.roi_start_x
            self.pixel_to_wavelength = np.linspace(self.start_wavelength, self.end_wavelength, num_pixels)

        # Set up the plot for real-time spectrum updates
        self.ax.set_xlabel('Wavelength (nm)')
        self.ax.set_ylabel('Intensity')
        self.ax.set_title('Real-time Spectral Intensity')

    def update_frame(self):
        """Continuously update the webcam feed and ROI in real-time."""
        # Read a frame from the webcam
        ret, frame = self.cap.read()

        if ret:
            # Convert the frame to RGB (since OpenCV uses BGR by default)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Draw the selected ROI rectangle on the frame (if ROI is selected)
            if self.roi_start_x and self.roi_start_y and self.roi_end_x and self.roi_end_y:
                cv2.rectangle(rgb_frame, (self.roi_start_x, self.roi_start_y), 
                              (self.roi_end_x, self.roi_end_y), (255, 0, 0), 2)

                # Extract the ROI if selection is finalized
                if not self.selecting_roi:
                    roi = rgb_frame[self.roi_start_y:self.roi_end_y, self.roi_start_x:self.roi_end_x]

                    # Process the ROI (for example, display it and map wavelengths)
                    self.update_roi_window(roi)

                    # If calibration is done, sum the columns and update the graph
                    if self.pixel_to_wavelength is not None:
                        self.plot_spectrum(roi)

            # Convert frame to an image format Tkinter can display
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)

            # Update the label with the new frame
            self.label.imgtk = imgtk
            self.label.configure(image=imgtk)

        # Repeat after 10 ms
        self.root.after(10, self.update_frame)

    def plot_spectrum(self, roi):
        """Sum the columns of the ROI and update the intensity graph in real-time."""
        # Sum the columns to get the intensity for each column (wavelength)
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        column_sum = np.sum(roi_gray, axis=0)  # Sum along the vertical axis

        # Update the plot with the new data
        self.line.set_xdata(self.pixel_to_wavelength)
        self.line.set_ydata(column_sum)
        self.ax.relim()  # Recalculate limits
        self.ax.autoscale_view(True, True, True)  # Autoscale the view to fit new data
        self.fig.canvas.draw()  # Redraw the figure

    def save_spectrum(self):
        """Save the ROI and calibration data."""
        if self.roi_start_x and self.roi_end_x and self.pixel_to_wavelength is not None:
            # Ask the user to choose a file name to save the spectrum
            save_dir = filedialog.askdirectory(title="Select Directory to Save Spectrum")
            if save_dir:
                # Save the ROI image
                roi = self.cap.read()[1][self.roi_start_y:self.roi_end_y, self.roi_start_x:self.roi_end_x]
                roi_filename = os.path.join(save_dir, "spectrum_roi.png")
                cv2.imwrite(roi_filename, roi)

                # Save the calibration data
                calibration_data = {
                    "start_wavelength": self.start_wavelength,
                    "end_wavelength": self.end_wavelength,
                }
                calibration_filename = os.path.join(save_dir, "calibration_data.json")
                with open(calibration_filename, "w") as f:
                    json.dump(calibration_data, f)

                messagebox.showinfo("Save Successful", "Spectrum and calibration data saved successfully!")

    def reload_spectrum(self):
        """Reload a previously saved spectrum and calibration data."""
        # Ask the user for the saved spectrum image and calibration data
        roi_filename = filedialog.askopenfilename(title="Open Saved ROI Image", filetypes=[("Image Files", "*.png")])
        calibration_filename = filedialog.askopenfilename(title="Open Calibration Data", filetypes=[("JSON Files", "*.json")])

        if roi_filename and calibration_filename:
            # Load the saved ROI image
            self.saved_roi_image = cv2.imread(roi_filename)
            self.update_roi_window(self.saved_roi_image)

            # Load the calibration data
            with open(calibration_filename, "r") as f:
                calibration_data = json.load(f)
                self.start_wavelength = calibration_data["start_wavelength"]
                self.end_wavelength = calibration_data["end_wavelength"]

            # Recalculate pixel-to-wavelength mapping
            num_pixels = self.saved_roi_image.shape[1]
            self.pixel_to_wavelength = np.linspace(self.start_wavelength, self.end_wavelength, num_pixels)

            # Plot the saved spectrum
            self.plot_spectrum(self.saved_roi_image)

    def on_close(self):
        """Clean up resources before exiting the application."""
        self.cap.release()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SpectrumAnalyzerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
