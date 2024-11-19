import cv2
import tkinter as tk
from tkinter import ttk
from tkinter import Label, Toplevel, simpledialog, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
import json


class SpectrumAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Webcam Spectrum Analyzer")
        
        self.cap = None
        self.active = False
        self.webcam_id : int = 0

        self.select_cam()

        self.flipped = False

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
        #self.fig.canvas.set_window_title("Spectrum") # Name the matplotlib window

        # Add a menu for saving/reloading/recalibrating/reselecting the spectrum
        self.create_menu()

        # Bind mouse events for ROI selection
        self.label.bind("<ButtonPress-1>", self.on_mouse_down)  # Left-click to start ROI
        self.label.bind("<B1-Motion>", self.on_mouse_drag)       # Dragging the mouse
        self.label.bind("<ButtonRelease-1>", self.on_mouse_up)   # Release to finalize ROI

        # Update the frame every 10 ms
        self.update_frame()

    def create_menu(self):
        """Create a menu for saving, reloading, and recalibrating the spectrum."""
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Save Calibration Data", command=self.save_spectrum)
        filemenu.add_command(label="Reload Calibration Data", command=self.reload_spectrum)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=filemenu)

        spectrummenu = tk.Menu(menubar, tearoff=0)
        spectrummenu.add_command(label="Flip horizontally", command=self.flip)
        spectrummenu.add_command(label="Select different camera", command=self.select_cam)
        spectrummenu.add_command(label="Recalibrate Spectrum", command=self.recalibrate)
        spectrummenu.add_command(label="Reselect ROI", command=self.reselect)
        menubar.add_cascade(label="Spectrum", menu=spectrummenu)

        self.root.config(menu=menubar)

    def flip(self):
        self.flipped = not self.flipped

    def list_webcams(self) -> list[int]:
        i = 0
        arr = []
        while i < 10:
            try:
                cap = cv2.VideoCapture(i)
                if cap.read()[0]:
                    arr.append(i)
                cap.release()
            except:
                pass
            i += 1
        return arr
        return [0,1,2,3,4]
    
    def select_cam(self) -> int:
        cams = self.list_webcams()
        # Create a new Toplevel window
        popup = tk.Toplevel(self.root)
        self.root
        popup.title("Select Webcam")
        popup.geometry("300x200")  # Set size of the popup window

        # Add a label to the popup window
        ttk.Label(popup, text="Please choose the webcam:").pack(pady=10)

        # Dropdown (Combobox) inside the popup
        selected_option = tk.IntVar(value=cams[0])  # Default value
        dropdown = ttk.Combobox(popup, textvariable=selected_option, values=cams, state="readonly")
        dropdown.pack(pady=10)

        def confirm_selection():
            self.active = False
            self.webcam_id = selected_option.get()
            popup.destroy()  # Close the popup
            if self.cap != None: # Delete old cap
                self.cap.release()
            # Capture video from webcam
            self.cap = cv2.VideoCapture(self.webcam_id)
            self.active = True

        ttk.Button(popup, text="OK", command=confirm_selection).pack(pady=10)


    def on_mouse_down(self, event):
        """Callback when the mouse button is pressed down, starting the ROI selection."""
        if self.roi_start_x == None:
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
            #Allow selecting in both directions
            if self.roi_start_x > self.roi_end_x:
                self.roi_start_x, self.roi_end_x = self.roi_end_x, self.roi_start_x
            if self.roi_start_y > self.roi_end_y:
                self.roi_start_y, self.roi_end_y = self.roi_end_y, self.roi_start_y

            # Create a new window to display the ROI
            self.show_roi_window()
            # After selecting the ROI, prompt the user for wavelength calibration
            self.calibrate_wavelengths()

    def show_roi_window(self):
        """Create a separate window to display the selected ROI."""
        if not self.roi_window:
            self.roi_window = Toplevel(self.root)
            self.roi_window.title("Selected Spectrum")
            icon = tk.PhotoImage(file="software/spectrometer.png")
            self.roi_window.iconphoto(False, icon)
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
        self.start_wavelength = float(simpledialog.askstring("Calibration", "Enter the start wavelength (e.g., 400 nm):").removeprefix("nm"))
        self.end_wavelength = float(simpledialog.askstring("Calibration", "Enter the end wavelength (e.g., 700 nm):").removeprefix("nm"))

        # Calculate pixel-to-wavelength mapping
        if self.roi_start_x and self.roi_end_x:
            num_pixels = self.roi_end_x - self.roi_start_x
            self.pixel_to_wavelength = np.linspace(self.start_wavelength, self.end_wavelength, num_pixels)

        # Set up the plot for real-time spectrum updates
        self.ax.set_xlabel("Wavelength (nm)")
        self.ax.set_ylabel("Intensity")
        self.ax.set_title("Spectral Intensity")

    def recalibrate(self):

        self.start_wavelength = float(simpledialog.askstring("Calibration", "Enter the start wavelength (e.g., 400 nm):", initialvalue="400").removeprefix("nm"))
        self.end_wavelength = float(simpledialog.askstring("Calibration", "Enter the end wavelength (e.g., 700 nm):", initialvalue="700").removeprefix("nm"))

        if self.roi_start_x and self.roi_end_x:
            num_pixels = self.roi_end_x - self.roi_start_x
            self.pixel_to_wavelength = np.linspace(self.start_wavelength, self.end_wavelength, num_pixels)

    def reselect(self):

        self.roi_start_x = None
        self.roi_start_y = None
        self.roi_end_x = None
        self.roi_end_y = None
        self.selecting_roi = False
        self.pixel_to_wavelength = None

        if self.roi_window:
                self.roi_window.destroy()
                self.roi_window = None

    def update_frame(self):
        """Continuously update the webcam feed and ROI in real-time."""
        if self.active == True:
            # Read a frame from the webcam
            ret, frame = self.cap.read()
            
            if self.flipped == True:
                frame = cv2.flip(frame, 1) #Flip each Frame if flip is selected
    
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

    def wavelength_to_rgb(self, wavelength, gamma=0.8):
        wavelength = float(wavelength)
        if wavelength >= 380 and wavelength <= 750:
            A = 1.0
        else:
            A=0.5
        if wavelength < 380:
            wavelength = 380.
        if wavelength >750:
            wavelength = 750.
        if wavelength >= 380 and wavelength <= 440:
            attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
            R = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
            G = 0.0
            B = (1.0 * attenuation) ** gamma
        elif wavelength >= 440 and wavelength <= 490:
            R = 0.0
            G = ((wavelength - 440) / (490 - 440)) ** gamma
            B = 1.0
        elif wavelength >= 490 and wavelength <= 510:
            R = 0.0
            G = 1.0
            B = (-(wavelength - 510) / (510 - 490)) ** gamma
        elif wavelength >= 510 and wavelength <= 580:
            R = ((wavelength - 510) / (580 - 510)) ** gamma
            G = 1.0
            B = 0.0
        elif wavelength >= 580 and wavelength <= 645:
            R = 1.0
            G = (-(wavelength - 645) / (645 - 580)) ** gamma
            B = 0.0
        elif wavelength >= 645 and wavelength <= 750:
            attenuation = 0.3 + 0.7 * (750 - wavelength) / (750 - 645)
            R = (1.0 * attenuation) ** gamma
            G = 0.0
            B = 0.0
        else:
            R = 0.0
            G = 0.0
            B = 0.0
        return (R, G, B, A)


    def plot_spectrum(self, roi):
        """Sum the columns of the ROI and update the intensity graph in real-time."""
        # Sum the columns to get the intensity for each column (wavelength)
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
        column_sum = np.sum(roi_gray, axis=0)  # Sum along the vertical axis

        # Ignore the first and last few columns to avoid edge effects
        column_sum = column_sum[2:-2]
        wavelength_range = self.pixel_to_wavelength[2:-2]


        # Create colorlist
        wl = np.arange(self.start_wavelength, self.end_wavelength + 1, 2)
        colorlist = [self.wavelength_to_rgb(w) for w in wl]
        
        # Clear Plot
        self.ax.cla()

        # Update the plot with the new data
        self.line.set_xdata(wavelength_range)
        self.line.set_ydata(column_sum)
        self.ax.relim()
        self.ax.autoscale_view(True, True, True)  # Autoscale the view to fit new data

        # Color surface under plot with correct color (according to wavelength)
        #for i in range(self.roi_end_x - self.roi_start_x - 1):
        #   self.ax.fill_between(wavelength_range[i:i+2], 0, column_sum[i:i+1], color=colorlist[i])
        self.ax.fill_between(wavelength_range, 0, column_sum)
        
        self.fig.canvas.draw()  # Redraw the figure

    def save_spectrum(self):
        """Save the ROI and calibration data."""
        if self.roi_start_x and self.roi_end_x and self.pixel_to_wavelength is not None:
            # Ask the user to choose a file name to save the spectrum
            filename = filedialog.asksaveasfile(title="Save calibration data as", defaultextension=".json", filetypes=[("JSON Files", "*.json")])

            if filename:
                calibration_data = {
                    "webcam_id": self.webcam_id,
                    "flipped": self.flipped,
                    "start_wavelength": self.start_wavelength,
                    "end_wavelength": self.end_wavelength,
                    "roi_start": (self.roi_start_x, self.roi_start_y),
                    "roi_end": (self.roi_end_x, self.roi_end_y),
                    "webcam_id" : self.webcam_id,
                }

                json.dump(calibration_data, filename)
                filename.close()

                messagebox.showinfo("Save Successful", "Calibration data saved successfully!")

    def reload_spectrum(self):
        """Reload a previously saved spectrum and calibration data."""
        # Ask the user for the saved spectrum image and calibration data
        filename = filedialog.askopenfilename(title="Open Calibration Data", filetypes=[("JSON Files", "*.json")])

        if filename:
            # Load the calibration data
            try:
                with open(filename, "r") as f:
                    calibration_data = json.load(f)
                self.active = False
                old_webcam_id = self.webcam_id

                self.start_wavelength = calibration_data["start_wavelength"]
                self.end_wavelength = calibration_data["end_wavelength"]
                self.roi_start_x, self.roi_start_y = calibration_data["roi_start"]
                self.roi_end_x, self.roi_end_y = calibration_data["roi_end"]
                self.flipped = calibration_data["flipped"]
                self.webcam_id = calibration_data["webcam_id"]

                if self.cap != None: # Delete old cap
                    self.cap.release()
                try:
                    self.cap = cv2.VideoCapture(self.webcam_id)
                except:
                    try:
                        self.cap = cv2.VideoCapture(old_webcam_id)
                    except:
                        pass
                self.active=True

                self.show_roi_window() # Show ROI if ROI window is not currently shown

                # Recalculate pixel-to-wavelength mapping
                num_pixels = self.roi_end_x - self.roi_start_x
                self.pixel_to_wavelength = np.linspace(self.start_wavelength, self.end_wavelength, num_pixels)

                self.ax.set_xlabel("Wavelength (nm)")
                self.ax.set_ylabel("Intensity")
                self.ax.set_title("Spectral Intensity")
            except:
                messagebox.showerror("Recall Error", "Could not load calibration data from file")


    def on_close(self):
        """Clean up resources before exiting the application."""
        self.cap.release()
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    icon = tk.PhotoImage(file="software/spectrometer.png")
    root.iconphoto(False, icon)
    app = SpectrumAnalyzerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
