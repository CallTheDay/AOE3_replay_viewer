import tkinter as tk
import customtkinter
from tkinter import filedialog
from PIL import Image, ImageTk
import cv2
import Data_collection
import threading
import sys
from datetime import datetime

customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("dark-blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.loading_thread = None
        self.splash_root = None

        # variables definition
        self.data_collection_thread = None
        self.images = []  # for rectangles in canvas

        self.canvas = None
        self.video = None
        self.optionmenu_frame = None
        self.optionmenu_var = None
        self.option_label = None
        self.show_label = None
        self.attacks = None
        self.lost_vils = None
        self.idle_vils = None
        self.floating_resources = None
        self.attacks_checkbox = None
        self.lost_vils_checkbox = None
        self.idle_vils_checkbox = None
        self.floating_resources_checkbox = None
        self.pause_video = None
        self.play_button = None
        self.skip_button = None
        self.time_label = None
        self.restart_button = None
        self.select_button = None
        self.video_frame = None
        self.video_canvas = None
        self.cap = None
        self.current_video_position_seconds = None

        self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mkv")])
        self.start_loading_screen()
        self.start_data_collection(self.video_path)
        self.withdraw()

        self.close = False

    def terminate_program(self):
        # terminate all threads and end program
        self.close = True
        Data_collection.stop_running()
        if self.loading_thread and self.loading_thread.is_alive():
            self.loading_thread.join(timeout=0)

        if self.splash_root:
            self.splash_root.destroy()
        sys.exit()

    def loading_screen(self):
        self.splash_root = tk.Toplevel(self)
        self.splash_root.title("AOE III replay viewer")
        self.splash_root.geometry("1000x500")
        self.splash_root.resizable(False, False)
        self.splash_root.protocol("WM_DELETE_WINDOW", self.terminate_program)
        ico = Image.open("./assets/aoeIcon.png")
        photo = ImageTk.PhotoImage(ico)
        self.wm_iconphoto(False, photo)
        self.splash_root.wm_iconphoto(False, photo)

        loading_image = tk.PhotoImage(file="./assets/loading_screen_wt.PNG")
        loading_image_label = tk.Label(self.splash_root, image=loading_image)
        loading_image_label.image = loading_image
        loading_image_label.pack()

        loading_progress_label = tk.Label(self.splash_root, text="")
        loading_progress_label.place(relx=0.5, rely=0.4, anchor="center")

        def update_loading_progress():
            progress = Data_collection.loading_progress
            loading_progress_label.configure(text=progress)
            if not self.close:
                self.splash_root.after(8000, update_loading_progress)

        self.splash_root.after(100, update_loading_progress)

    def start_loading_screen(self):
        self.loading_thread = threading.Thread(target=self.loading_screen)
        self.loading_thread.start()

    @staticmethod
    def calculate_total_downtime(time_sequences):
        if not time_sequences:
            return "0m 0s"  # Handle empty input list

        total_seconds = 0

        for time_sequence in time_sequences:
            start_time_str, end_time_str = time_sequence.split('-')
            # Stripping leading/trailing whitespace
            start_time_str = start_time_str.strip()
            end_time_str = end_time_str.strip()

            # hours, minutes, and seconds
            start_time = datetime.strptime(start_time_str, '%H:%M:%S')
            end_time = datetime.strptime(end_time_str, '%H:%M:%S')

            # duration in seconds
            duration = (end_time - start_time).seconds
            total_seconds += duration

        # Converting to hours, minutes, seconds
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        result = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
        return result

    @staticmethod
    def calculate_lead_percentage(points_list):
        length = len(points_list)
        if length == 0:
            return "-"
        positives = 0
        for score in points_list:
            if score > 0:
                positives += 1
        return round(positives/(length/100))

    def check_data_collection(self, video_path):
        # Wait for data collection to finish
        Data_collection.run(video_path)

        self.attacks_list = Data_collection.population_death_times_list
        self.lost_vils_list = Data_collection.vil_death_times_list
        self.idle_vils_list = Data_collection.idle_vil_times_list
        self.floating_resources_list = Data_collection.floating_ressources_times_list
        self.after(0, self.update_option_menu)

        # Once data collection is finished, closing loading screen and opening main window
        if self.splash_root:
            self.splash_root.destroy()
        self.deiconify()
        self.main_window()

    def update_option_menu(self):
        self.attacks.configure(values=self.attacks_list)
        self.attacks.set("-")
        self.lost_vils.configure(values=self.lost_vils_list)
        self.lost_vils.set("-")
        self.idle_vils.configure(values=self.idle_vils_list)
        self.idle_vils.set("-")
        self.floating_resources.configure(values=self.floating_resources_list)
        self.floating_resources.set("-")

        # update summary labels
        lost_vils = len(Data_collection.vil_death_times_list)
        vil_downtime = self.calculate_total_downtime(Data_collection.idle_vil_times_list)
        floating_res = self.calculate_total_downtime(Data_collection.floating_ressources_times_list)
        lead_percentage = self.calculate_lead_percentage(Data_collection.final_points_list)
        lead = str(lead_percentage) + "%"
        self.lost_vils_sum_result_label.configure(text=str(lost_vils))
        self.villager_downtime_result_label.configure(text=("~" + str(vil_downtime)))
        self.suboptimal_ressources_result_label.configure(text=("~" + str(floating_res)))
        self.lead_result_label.configure(text=str(lead))

    def start_data_collection(self, video_path):
        self.data_collection_thread = threading.Thread(name="DataCollectionThread", target=self.check_data_collection, args=(video_path,))
        self.data_collection_thread.start()

    def main_window(self):
        self.title("AoE III Replay Viewer")
        self.geometry(f"{1300}x{850}")      # window size
        self.resizable(False, False)
        # grid layout
        self.grid_columnconfigure((1, 2), weight=0)
        self.grid_rowconfigure((0, 1, 2, 3), weight=0)
        # canvas (for graph and progress bar)
        self.canvas = customtkinter.CTkCanvas(width=862, height=332)
        self.canvas.grid(row=2, column=0, columnspan=1, padx=(10, 10), pady=0, sticky="nw")
        # video
        self.video = cv2.VideoCapture(self.video_path)

        def jump_to(time_str):
            if '-' in time_str:
                time_str = time_str.split('-', 1)[0]
            hours, minutes, seconds = map(int, time_str.split(':'))
            total_miliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000
            self.cap.set(cv2.CAP_PROP_POS_MSEC, total_miliseconds)

        def timestamp_to_seconds(timestamp):
            hours, minutes, seconds = map(int, timestamp.split(':'))
            total_seconds = hours * 3600 + minutes * 60 + seconds

            return total_seconds

        # for displaying timestamps on graph
        def show_timestamps(timestamps, is_duration=False):
            total_seconds = get_video_length_seconds()
            total_width = 775  # width of actual graph

            if is_duration:
                for value in timestamps:
                    time1 = value.split('-', 1)[0]
                    time2 = value.split('-', 1)[1]
                    time1_seconds = timestamp_to_seconds(time1)
                    time2_seconds = timestamp_to_seconds(time2)
                    x_pos = min(int((time1_seconds / total_seconds) * total_width), total_width)
                    x_pos2 = min(int((time2_seconds / total_seconds) * total_width), total_width)
                    self.create_rectangle(x_pos + 85, 25, x_pos2 + 85, 302, self.canvas, fill='green', alpha=0.5, tags="time_stamp")  # semi transparent
            else:
                for value in timestamps:    # apply new markings
                    position_seconds = timestamp_to_seconds(value)
                    x_pos = min(int((position_seconds / total_seconds) * total_width), total_width)
                    self.canvas.create_rectangle(x_pos + 85, 290, x_pos + 87, 302, fill='blue', outline='', tags="time_stamp")

        def checkbox_pressed():
            # delete old duration markings
            self.images = []
            image_path = "./assets/plots/cropped_new_plot.png"
            self.create_rectangle(0, 0, 830, 332, self.canvas, image_path)

            markings = self.canvas.find_withtag("time_stamp")
            for progress_bar_id in markings:  # delete old markings
                self.canvas.delete(progress_bar_id)

            if self.attacks_checkbox.get():  # Check status of checkbox
                show_timestamps(self.attacks_list)
            if self.idle_vils_checkbox.get():
                show_timestamps(self.idle_vils_list, True)
            if self.lost_vils_checkbox.get():
                show_timestamps(self.lost_vils_list)
            if self.floating_resources_checkbox.get():
                show_timestamps(self.floating_resources_list, True)

        # options buttons
        self.optionmenu_frame = customtkinter.CTkFrame(self)
        self.optionmenu_frame.grid(row=0, column=8, padx=(0, 0), pady=(10, 0), sticky="n")
        self.optionmenu_var = tk.IntVar(value=0)
        self.options_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Options")
        self.options_label.grid(row=0, column=0, columnspan=1, padx=20, pady=5, sticky="ne")
        self.show_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Timestamps")
        self.show_label.grid(row=0, column=1, columnspan=1, padx=20, pady=5, sticky="nw")

        self.attacks_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Attacks")
        self.attacks_label.grid(row=1, column=0, columnspan=1, padx=20, pady=5, sticky="ne")
        self.attacks = customtkinter.CTkOptionMenu(self.optionmenu_frame, dynamic_resizing=True, values=["-"], command=jump_to)
        self.attacks_list = Data_collection.population_death_times_list
        self.attacks.configure(values=self.attacks_list)
        self.attacks.grid(row=1, column=1, pady=10, padx=0, sticky="n")

        self.lost_vils_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Lost villagers")
        self.lost_vils_label.grid(row=2, column=0, columnspan=1, padx=20, pady=5, sticky="ne")
        self.lost_vils = customtkinter.CTkOptionMenu(self.optionmenu_frame, dynamic_resizing=True, values=["-"], command=jump_to)
        self.lost_vils_list = Data_collection.vil_death_times_list
        self.lost_vils.configure(values=self.lost_vils_list)
        self.lost_vils.grid(row=2, column=1, pady=10, padx=0, sticky="n")

        self.idle_vils_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Idle villagers")
        self.idle_vils_label.grid(row=3, column=0, columnspan=1, padx=20, pady=5, sticky="ne")
        self.idle_vils = customtkinter.CTkOptionMenu(self.optionmenu_frame, dynamic_resizing=True, values=["-"], command=jump_to)
        self.idle_vils_list = Data_collection.idle_vil_times_list
        self.idle_vils.configure(values=self.idle_vils_list)
        self.idle_vils.grid(row=3, column=1, pady=10, padx=0, sticky="n")

        self.floating_resources_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="Floating ressources")
        self.floating_resources_label.grid(row=4, column=0, columnspan=1, padx=20, pady=5, sticky="ne")
        self.floating_resources = customtkinter.CTkOptionMenu(self.optionmenu_frame, dynamic_resizing=True, values=["-"], command=jump_to)
        self.floating_resources_list = Data_collection.floating_ressources_times_list
        self.floating_resources.configure(values=self.floating_resources_list)
        self.floating_resources.grid(row=4, column=1, pady=10, padx=0, sticky="n")

        # options checkboxes
        self.attacks_checkbox = customtkinter.CTkCheckBox(master=self.optionmenu_frame, text="", command=checkbox_pressed)
        self.attacks_checkbox.grid(row=1, column=2, pady=(10, 0), padx=0, sticky="n")
        self.lost_vils_checkbox = customtkinter.CTkCheckBox(master=self.optionmenu_frame, text="", command=checkbox_pressed)
        self.lost_vils_checkbox.grid(row=2, column=2, pady=10, padx=0, sticky="n")
        self.idle_vils_checkbox = customtkinter.CTkCheckBox(master=self.optionmenu_frame, text="", command=checkbox_pressed)
        self.idle_vils_checkbox.grid(row=3, column=2, pady=(10, 0), padx=20, sticky="n")
        self.floating_resources_checkbox = customtkinter.CTkCheckBox(master=self.optionmenu_frame, text="", command=checkbox_pressed)
        self.floating_resources_checkbox.grid(row=4, column=2, pady=10, padx=20, sticky="n")

        # play/pause button
        self.pause_video = False

        def toggle_pause():
            self.pause_video = not self.pause_video
            if not self.pause_video:
                # if video is unpaused, start update_video again
                update_video()

        self.play_button = customtkinter.CTkButton(self.optionmenu_frame, command=toggle_pause, text="Play/Pause Video")
        self.play_button.grid(row=5, column=0, padx=20, pady=10)

        # forward/backward button
        def skip(skipforward, time):
            current_pos = self.cap.get(cv2.CAP_PROP_POS_MSEC)  # Get current position in milliseconds
            if skipforward:
                new_pos = current_pos + time  # Add 10 seconds (10,000 milliseconds)
            else:
                new_pos = current_pos - time
            self.cap.set(cv2.CAP_PROP_POS_MSEC, new_pos)  # Set the new position

        self.skip_button = customtkinter.CTkButton(self.optionmenu_frame, command=lambda: skip(True, 10000), text=">")
        self.skip_button.grid(row=6, column=1, padx=20, pady=10)
        self.skip_button = customtkinter.CTkButton(self.optionmenu_frame, command=lambda: skip(False, 10000), text="<")
        self.skip_button.grid(row=6, column=0, padx=20, pady=10)
        self.skip_button = customtkinter.CTkButton(self.optionmenu_frame, command=lambda: skip(True, 60000), text=">>")
        self.skip_button.grid(row=7, column=1, padx=20, pady=10)
        self.skip_button = customtkinter.CTkButton(self.optionmenu_frame, command=lambda: skip(False, 60000), text="<<")
        self.skip_button.grid(row=7, column=0, padx=20, pady=10)

        def skip_to_timepoint(timepoint):
            parts = timepoint.split(':')

            try:
                if len(parts) == 3:  # Format "h:m:s"
                    hours, minutes, seconds = map(int, parts)
                    timepoint_formatted = (hours * 3600 + minutes * 60 + seconds) * 1000
                elif len(parts) == 2:  # Format "m:s"
                    minutes, seconds = map(int, parts)
                    timepoint_formatted = (minutes * 60 + seconds) * 1000
                elif len(parts) == 1:  # Format "s"
                    seconds = int(parts[0])
                    timepoint_formatted = seconds * 1000
                else:
                    return  # invalid input like 40:32:02:45 is ignored
            except ValueError:
                return  # invalid input like 40:a:abc is ignored

            self.cap.set(cv2.CAP_PROP_POS_MSEC, timepoint_formatted)

        self.entry = customtkinter.CTkEntry(self.optionmenu_frame, placeholder_text="Choose time")
        self.entry.grid(row=8, column=0, columnspan=1, padx=20, pady=10, sticky="nsew")

        self.go_to_timepoint = customtkinter.CTkButton(self.optionmenu_frame, command=lambda: skip_to_timepoint(self.entry.get()), text="Go to time")
        self.go_to_timepoint.grid(row=8, column=1, padx=20, pady=10)

        # video progress time label
        self.time_label = customtkinter.CTkLabel(master=self.optionmenu_frame, text="")
        self.time_label.grid(row=9, column=1, padx=20, pady=10)

        def update_time_label():
            formatted_time = time_formatted()
            self.time_label.configure(text=formatted_time)

        # restart button
        def restart():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.restart_button = customtkinter.CTkButton(self.optionmenu_frame, command=restart, text="Restart")
        self.restart_button.grid(row=5, column=1, padx=20, pady=10)

        # select new video to analyze
        def select_video():
            self.pause_video = True
            self.video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi;*.mkv")])

            self.attacks_list = []
            self.lost_vils_list = []
            self.idle_vils_list = []
            self.floating_resources_list = []
            self.update_option_menu()

            self.start_loading_screen()
            self.start_data_collection(self.video_path)
            self.withdraw()

        self.select_button = customtkinter.CTkButton(self.optionmenu_frame, command=select_video, text="Select Video")
        self.select_button.grid(row=9, column=0, padx=20, pady=10)

        self.summenu_frame = customtkinter.CTkFrame(self)
        self.summenu_frame.grid(row=2, column=8, padx=(0, 0), pady=(10, 0), sticky="nw")
        self.sum_label = customtkinter.CTkLabel(master=self.summenu_frame, text="Game summary")
        self.sum_label.grid(row=0, column=0, columnspan=1, padx=20, pady=5, sticky="nw")
        self.lost_vils_sum_label = customtkinter.CTkLabel(master=self.summenu_frame, text="Villager raids (on P1):")
        self.lost_vils_sum_label.grid(row=1, column=0, columnspan=1, padx=20, pady=5, sticky="nw")
        self.villager_downtime_label = customtkinter.CTkLabel(master=self.summenu_frame, text="Villager downtime (idle):")
        self.villager_downtime_label.grid(row=2, column=0, columnspan=1, padx=20, pady=5, sticky="nw")
        self.suboptimal_ressources_label = customtkinter.CTkLabel(master=self.summenu_frame, text="Floating ressources time:")
        self.suboptimal_ressources_label.grid(row=3, column=0, columnspan=1, padx=20, pady=5, sticky="nw")
        self.lead_label = customtkinter.CTkLabel(master=self.summenu_frame, text="P1 lead time (% of game):")
        self.lead_label.grid(row=4, column=0, columnspan=1, padx=20, pady=5, sticky="nw")

        self.lost_vils_sum_result_label = customtkinter.CTkLabel(master=self.summenu_frame, text="-")
        self.lost_vils_sum_result_label.grid(row=1, column=1, columnspan=1, padx=20, pady=5, sticky="nw")
        self.villager_downtime_result_label = customtkinter.CTkLabel(master=self.summenu_frame, text="-")
        self.villager_downtime_result_label.grid(row=2, column=1, columnspan=1, padx=20, pady=5, sticky="nw")
        self.suboptimal_ressources_result_label = customtkinter.CTkLabel(master=self.summenu_frame, text="-")
        self.suboptimal_ressources_result_label.grid(row=3, column=1, columnspan=1, padx=20, pady=5, sticky="nw")
        self.lead_result_label = customtkinter.CTkLabel(master=self.summenu_frame, text="-")
        self.lead_result_label.grid(row=4, column=1, columnspan=1, padx=20, pady=5, sticky="nw")

        def summary_labels():
            lost_vils = len(Data_collection.vil_death_times_list)
            vil_downtime = self.calculate_total_downtime(Data_collection.idle_vil_times_list)
            floating_res = self.calculate_total_downtime(Data_collection.floating_ressources_times_list)
            lead_percentage = self.calculate_lead_percentage(Data_collection.final_points_list)
            lead = str(lead_percentage) + "%"

            self.lost_vils_sum_result_label.configure(text=str(lost_vils))
            self.villager_downtime_result_label.configure(text=("~" + str(vil_downtime)))
            self.suboptimal_ressources_result_label.configure(text=("~" + str(floating_res)))
            self.lead_result_label.configure(text=str(lead))

        summary_labels()

        # video player
        self.video_frame = tk.Frame(self)
        self.video_frame.grid(row=0, column=0, columnspan=8, padx=(10, 10), pady=10, sticky="nw")
        self.video_canvas = tk.Canvas(self.video_frame)
        self.video_canvas.pack(fill=tk.BOTH, expand=False)

        self.cap = self.video

        # get total video length
        def get_video_length_seconds():
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = round(self.cap.get(cv2.CAP_PROP_FPS))
            video_length_seconds = int(total_frames / fps)
            return video_length_seconds

        # custom progress bar (within graph)
        def progress_bar():
            total_seconds = get_video_length_seconds()
            current_position = self.current_video_position_seconds
            total_width = 774  # width of actual graph
            progress_width = int((current_position / total_seconds) * total_width)

            # Update progress bar on canvas
            self.update_progress_bar(progress_width+86, progress_width+87)

        # video progress
        self.current_video_position_seconds = 0

        def time_formatted():
            seconds = self.current_video_position_seconds

            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # display video in gui
        def update_video():
            if not self.pause_video:
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = Image.fromarray(frame)
                    new_width = 862
                    new_height = 485
                    frame = frame.resize((new_width, new_height))

                    # Convert to PhotoImage
                    frame = ImageTk.PhotoImage(image=frame)

                    # update video progress bar
                    self.current_video_position_seconds = int(self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
                    progress_bar()
                    update_time_label()

                    # resizing canvas/display
                    self.video_canvas.config(width=new_width, height=new_height)
                    self.video_canvas.create_image(0, 0, anchor=tk.NW, image=frame)
                    self.video_canvas.image = frame

                    self.after(20, update_video)  # can be adjusted for better/worse video smoothness but higher/lower cpu utilization

        update_video()
        image_path = "./assets/plots/cropped_new_plot.png"
        self.create_rectangle(0, 0, 830, 350, self.canvas, image_path)

    def update_progress_bar(self, x1, x2):
        # deletes previous progress rectangle and draws new one (simulating moving bar)
        progress_bar_ids = self.canvas.find_withtag("progress_bar")

        for progress_bar_id in progress_bar_ids:
            self.canvas.delete(progress_bar_id)

        self.canvas.create_rectangle(x1, 25, x2, 302, fill='black', tags="progress_bar")

    # custom create rectangle function which allows transparency
    def create_rectangle(self, x1, y1, x2, y2, canvas, image_path=None, **kwargs):
        if image_path:
            image = Image.open(image_path)
            self.images.append(ImageTk.PhotoImage(image))
            canvas.create_image(x1, y1, image=self.images[-1], anchor='nw')
        else:
            if 'alpha' in kwargs:
                alpha = int(kwargs.pop('alpha') * 255)
                fill = kwargs.pop('fill')
                fill = self.canvas.winfo_rgb(fill) + (alpha,)
                image = Image.new('RGBA', (x2 - x1, y2 - y1), fill)
                self.images.append(ImageTk.PhotoImage(image))
                canvas.create_image(x1, y1, image=self.images[-1], anchor='nw')
                canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
            else:
                canvas.create_rectangle(x1, y1, x2, y2, outline='', **kwargs)


if __name__ == "__main__":
    app = App()
    app.mainloop()

