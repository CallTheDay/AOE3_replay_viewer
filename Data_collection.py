import cv2
import easyocr
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import sys
import time as ti
import os

running = False
video_path = ""
vil_death_times_list = []
idle_vil_times_list = []
population_death_times_list = []
floating_ressources_times_list = []
loading_progress = ""
final_points_list = []
small_UI = False

# variables for manually disabling elements and changing sampling frequency
show_attacks = True
show_villager_deaths = True
show_idle_villager = True
show_floating_ressources = True
custom_sampling_frequency = 10

def run(vid_path):
    global small_UI
    global loading_progress
    global final_points_list
    global UI_scale
    vil_death_times_list.clear()
    idle_vil_times_list.clear()
    population_death_times_list.clear()
    floating_ressources_times_list.clear()
    final_points_list.clear()
    loading_progress = "0%"
    small_UI = False

    start_time = ti.time()
    global running
    global video_path
    video_path = vid_path
    running = True

    def load_custom_settings(file_path='Custom_settings.txt'):
        global show_attacks, show_villager_deaths, show_idle_villager, show_floating_ressources, custom_sampling_frequency

        default_settings = {
            'show_attacks': True,
            'show_villager_deaths': True,
            'show_idle_villager': True,
            'show_floating_ressources': True,
            'custom_sampling_frequency': 10
        }

        if not os.path.exists(file_path):
            with open(file_path, 'w') as file:
                for key, value in default_settings.items():
                    file.write(f'{key} = {value}\n')
            return

        with open(file_path, 'r') as file:
            lines = file.readlines()

        settings = {}
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if key in default_settings:
                    if value.lower() in ['true', 'false']:
                        settings[key] = value.lower() == 'true'
                    elif key == 'custom_sampling_frequency':
                        try:
                            frequency = int(value)
                            if 1 <= frequency <= 60:    # sampling frequency can only between 1s and 60s
                                settings[key] = frequency
                            else:
                                settings[key] = default_settings[key]
                        except ValueError:
                            settings[key] = default_settings[key]
                    else:
                        settings[key] = default_settings[key]

        # Update global variables
        show_attacks = settings.get('show_attacks', default_settings['show_attacks'])
        show_villager_deaths = settings.get('show_villager_deaths', default_settings['show_villager_deaths'])
        show_idle_villager = settings.get('show_idle_villager', default_settings['show_idle_villager'])
        show_floating_ressources = settings.get('show_floating_ressources', default_settings['show_floating_ressources'])
        custom_sampling_frequency = settings.get('custom_sampling_frequency', default_settings['custom_sampling_frequency'])

    # load settings
    load_custom_settings()

    while running:
        # loading icons to be searched
        food_icon = cv2.imread("./assets/food.PNG")
        food_gray = cv2.cvtColor(food_icon, cv2.COLOR_BGR2GRAY)
        food_icon_80 = cv2.imread("./assets/food_small.png")      # for games with ui at 80%
        food_gray_80 = cv2.cvtColor(food_icon_80, cv2.COLOR_BGR2GRAY)
        game_identifier_image = cv2.imread("./assets/game_started.png")
        game_identifier_gray = cv2.cvtColor(game_identifier_image, cv2.COLOR_BGR2GRAY)
        game_80_identifier_image = cv2.imread("./assets/game_started_80.png")    # UI can be set at 100% or 80%
        game_80_identifier_gray = cv2.cvtColor(game_80_identifier_image, cv2.COLOR_BGR2GRAY)
        replay_identifier = cv2.imread("./assets/replay_identifier.png")
        replay_identifier_gray = cv2.cvtColor(replay_identifier, cv2.COLOR_BGR2GRAY)

        # Load video
        cap = cv2.VideoCapture(video_path)
        # frame rate
        fps = round(cap.get(cv2.CAP_PROP_FPS))     # some videos are not exact. For example 29.7fps

        # Initialize frame counter
        frame_counter = 0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        total_duration_seconds = total_frames / fps

        # easyocr Reader (for detecting digits and letters from pictures)
        reader = easyocr.Reader(['en'], gpu=False)

        # flags and variables
        game_started_flag = False
        stop = False
        is_a_replay = False
        food_pos_found_flag = False
        food_x1 = 0
        food_y1 = 0

        idle_vil_list = []
        vil_count_list = []
        population_list = []
        food_list = []
        wood_list = []
        coin_list = []

        p1_score_list = []
        p2_score_list = []
        delta_score_list = []

        # Screenshot of video every x seconds (sampling frequency)
        # sampling_frequency = 10
        sampling_frequency = custom_sampling_frequency
        elapsed_time = 0

        while cap.isOpened() and running:

            # Read next frame
            ret, frame = cap.read()
            if not ret:
                break

            frame_counter += 1
            frame = cv2.resize(frame, (1920, 1080))  # scale frame to correct size 1080p

            if frame_counter % (int(fps) * sampling_frequency) == 0:  # get frame corresponding to desired time
                loading_progress = str(round(frame_counter / (total_frames / 100))) + "%"
                print(loading_progress)
                elapsed_time += sampling_frequency
                screenshot_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                game_identifier_pos = cv2.matchTemplate(screenshot_gray, game_identifier_gray, cv2.TM_CCOEFF_NORMED)
                game_80_identifier_pos = cv2.matchTemplate(screenshot_gray, game_80_identifier_gray, cv2.TM_CCOEFF_NORMED)

                # check if score visible
                accuracy_threshold = 0.75

                if cv2.minMaxLoc(game_identifier_pos)[1] > accuracy_threshold:
                    game_started_flag = True
                    game_identifier_visible = True
                elif cv2.minMaxLoc(game_80_identifier_pos)[1] > accuracy_threshold:
                    game_started_flag = True
                    game_identifier_visible = True
                    small_UI = True
                else:
                    game_identifier_visible = False

                # time check if game has started and if it is a replay
                if game_identifier_visible and not stop:
                    print("Game starts at: {:02d}:{:02d}".format(int(elapsed_time // 60), int(elapsed_time % 60)))
                    replay_menue_pos = cv2.matchTemplate(screenshot_gray, replay_identifier_gray, cv2.TM_CCOEFF_NORMED)
                    if cv2.minMaxLoc(replay_menue_pos)[1] > accuracy_threshold:
                        is_a_replay = True
                    stop = True

                if game_started_flag:
                    # check the food position only once (different pos for certain civilizations and HUD)
                    if not food_pos_found_flag:
                        # food
                        if small_UI:
                            food_pos = cv2.matchTemplate(screenshot_gray, food_gray_80, cv2.TM_CCOEFF_NORMED)
                        else:
                            food_pos = cv2.matchTemplate(screenshot_gray, food_gray, cv2.TM_CCOEFF_NORMED)
                        # top left and bottom right location of searched icon
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(food_pos)
                        top_left = max_loc
                        bottom_right = (top_left[0] + food_gray.shape[1], top_left[1] + food_gray.shape[0])
                        # region of interest (ressource digit field)
                        food_y1 = top_left[1]
                        food_x1 = top_left[0]
                        food_pos_found_flag = True

                    # cropping out the various fields (hard coded pixel values)
                    # depending on found food pos and depending on UI scale
                    if not small_UI:
                        idle_vil_crop = frame[(food_y1+105):(food_y1+128), (food_x1-52):(food_x1-18)]
                        vil_count_crop = frame[(food_y1+108):(food_y1+127), (food_x1+23):(food_x1+51)]
                        population_crop = frame[(food_y1 - 33):(food_y1 - 10), (food_x1 + 20):(food_x1 + 130)]
                        food_crop = frame[(food_y1 + 1):(food_y1 + 24), (food_x1 + 24):(food_x1 + 130)]
                        wood_crop = frame[(food_y1 + 36):(food_y1 + 59), (food_x1 + 24):(food_x1 + 130)]
                        coin_crop = frame[(food_y1 + 71):(food_y1 + 94), (food_x1 + 24):(food_x1 + 130)]
                    else:
                        idle_vil_crop = frame[(food_y1 + 81):(food_y1 + 101), (food_x1 - 38):(food_x1 - 11)]
                        vil_count_crop = frame[(food_y1 + 81):(food_y1 + 101), (food_x1 + 21):(food_x1 + 51)]
                        population_crop = frame[(food_y1 - 33):(food_y1 - 12), (food_x1 + 20):(food_x1 + 110)]
                        food_crop = frame[(food_y1 - 2):(food_y1 + 18), (food_x1 + 22):(food_x1 + 110)]
                        wood_crop = frame[(food_y1 + 24):(food_y1 + 44), (food_x1 + 22):(food_x1 + 110)]
                        coin_crop = frame[(food_y1 + 54):(food_y1 + 74), (food_x1 + 22):(food_x1 + 110)]

                    cv2.rectangle(frame, ((food_x1 - 40), food_y1 + 81), ((food_x1 - 12), (food_y1 + 101)), (0, 255, 0), 2)

                    # score position
                    # different postion of scores depending if it is direct capture or replay capture
                    # and depending if it is the small or large UI in the game
                    if is_a_replay:
                        if not small_UI:
                            score_player_one_tl = (1805, 275)  # position of player 1 score
                            score_player_one_br = (1880, 293)
                            score_player_two_tl = (1805, 305)  # position of player 2 score
                            score_player_two_br = (1880, 323)
                        else:
                            score_player_one_tl = (1825, 220)  # position of player 1 score
                            score_player_one_br = (1880, 233)
                            score_player_two_tl = (1825, 242)  # position of player 2 score
                            score_player_two_br = (1880, 256)
                    else:
                        if not small_UI:
                            score_player_one_tl = (1805, 125)  # position of player 1 score
                            score_player_one_br = (1880, 142)
                            score_player_two_tl = (1805, 154)  # position of player 2 score
                            score_player_two_br = (1880, 172)
                        else:
                            score_player_one_tl = (1830, 100)  # position of player 1 score
                            score_player_one_br = (1885, 115)
                            score_player_two_tl = (1830, 123)  # position of player 2 score
                            score_player_two_br = (1885, 138)

                    p1_score_crop = frame[score_player_one_tl[1]:score_player_one_br[1], score_player_one_tl[0]:score_player_one_br[0]]
                    p2_score_crop = frame[score_player_two_tl[1]:score_player_two_br[1], score_player_two_tl[0]:score_player_two_br[0]]

                    # READER (detecting values)
                    # increasing size and applying threshhold to better read values
                    # idle vils
                    if show_idle_villager:  # can be turned off using custom_settings.txt
                        resized_idle_vil_crop = cv2.resize(idle_vil_crop, (idle_vil_crop.shape[1] * 10, idle_vil_crop.shape[0] * 10))
                        idle_vils = reader.readtext(resized_idle_vil_crop, allowlist='0123456789')
                        for value in idle_vils:
                            if value[2] > 0.9:
                                idle_vil_list.append((int(value[1]), elapsed_time))

                    # vil count
                    if show_villager_deaths:
                        resized_vil_count_crop = cv2.resize(vil_count_crop, (vil_count_crop.shape[1] * 10, vil_count_crop.shape[0] * 10))
                        vil_count = reader.readtext(resized_vil_count_crop, allowlist='0123456789')
                        for value in vil_count:
                            if value[2] > 0.9:  # confidence score
                                vil_count_list.append((int(value[1]), (elapsed_time-sampling_frequency)))  # -sampling frequency to get to timepoint shortly before

                    # population count
                    if show_attacks:
                        resized_population_crop = cv2.resize(population_crop, (population_crop.shape[1] * 10, population_crop.shape[0] * 10))
                        population = reader.readtext(resized_population_crop, allowlist='0123456789/')
                        for value in population[:1]:
                            pop = value[1]
                            population_str = str(pop).split('/', 1)[0]
                            if value[2] > 0.9:  # confidence score
                                population_list.append((population_str, (elapsed_time-sampling_frequency)))

                    # food amount
                    if show_floating_ressources:
                        resized_food_crop = cv2.resize(food_crop, (food_crop.shape[1] * 10, food_crop.shape[0] * 10))
                        food_amount = reader.readtext(resized_food_crop, allowlist='0123456789')  # reads value like 578 (+49) as two seperate values (only first matters)
                        for value in food_amount[:1]:  # only iterate over first element
                            if value[2] > 0.7:
                                food_list.append((int(value[1]), elapsed_time))
                            else:
                                food_list.append((sys.maxsize, elapsed_time))

                        # wood amount
                        resized_wood_crop = cv2.resize(wood_crop, (wood_crop.shape[1] * 10, wood_crop.shape[0] * 10))
                        wood_amount = reader.readtext(resized_wood_crop, allowlist='0123456789')
                        for value in wood_amount[:1]:
                            if value[2] > 0.7:
                                wood_list.append((int(value[1]), elapsed_time))
                            else:
                                wood_list.append((sys.maxsize, elapsed_time))
                        if len(wood_list) < len(food_list):     # making sure that ressource lists are always same size
                            wood_list.append((sys.maxsize, elapsed_time))

                        # coin amount
                        resized_coin_crop = cv2.resize(coin_crop, (coin_crop.shape[1] * 10, coin_crop.shape[0] * 10))
                        coin_amount = reader.readtext(resized_coin_crop, allowlist='0123456789')
                        for value in coin_amount[:1]:
                            if value[2] > 0.7:
                                coin_list.append((int(value[1]), elapsed_time))
                            else:
                                coin_list.append((sys.maxsize, elapsed_time))
                        if len(coin_list) < len(food_list):
                            coin_list.append((sys.maxsize, elapsed_time))

                    # Reading scores
                    if game_identifier_visible:
                        # both lists should stay the same size. If the value for one list is not detected
                        # it should just add its previous value again.
                        prev_p1_score = None
                        prev_p2_score = None

                        # improve readability of numbers
                        resized_p1_score_crop = cv2.resize(p1_score_crop, (p1_score_crop.shape[1] * 4, p1_score_crop.shape[0] * 4))
                        _, p1_score_crop_threshhold = cv2.threshold(resized_p1_score_crop, 120, 255, cv2.THRESH_BINARY_INV)

                        # reading the improved picture
                        p1_score_added = False
                        p1_score = reader.readtext(p1_score_crop_threshhold, allowlist='0123456789')
                        for value in p1_score:
                            if value[1]:
                                p1_score_list.append((int(value[1]), elapsed_time))
                                prev_p1_score = int(value[1])
                                p1_score_added = True
                            # if no number is read, use previous.
                        if not p1_score_added:
                            if prev_p1_score is not None:
                                p1_score_list.append((prev_p1_score, elapsed_time))

                        # read p2 scores
                        resized_p2_score_crop = cv2.resize(p2_score_crop, (p2_score_crop.shape[1] * 4, p2_score_crop.shape[0] * 4))
                        _, p2_score_crop_threshhold = cv2.threshold(resized_p2_score_crop, 120, 255, cv2.THRESH_BINARY_INV)

                        p2_score_added = False
                        p2_score = reader.readtext(p2_score_crop_threshhold, allowlist='0123456789')
                        for value in p2_score:
                            if value[1]:
                                p2_score_list.append((int(value[1]), elapsed_time))
                                prev_p2_score = int(value[1])
                                p2_score_added = True
                        if not p2_score_added:
                            if prev_p2_score is not None:
                                p2_score_list.append((prev_p2_score, elapsed_time))

                    if not game_identifier_visible:   # leave score at previous visible points but make entry (to have correct times)
                        if len(p1_score_list) == 0:     # 0 if list is still empty
                            p1_score_list.append((0, elapsed_time))
                        p1_score_list.append((p1_score_list[-1][0], elapsed_time))
                        if len(p2_score_list) == 0:
                            p2_score_list.append((0, elapsed_time))
                        p2_score_list.append((p2_score_list[-1][0], elapsed_time))

                    # Show image (for debugging)
                    # cv2.imshow("screenshot", frame)
                    # cv2.imshow("a", p1_score_crop)
                    # cv2.imshow("b", p2_score_crop)
                    # cv2.imshow("c", resized_coin_crop)
                    # cv2.waitKey(0)  # Press any key to move to the next frame

        for i in range(len(p1_score_list)):
            delta_score = int(p1_score_list[i][0] - p2_score_list[i][0])
            # stop if delta score is the same as score 1 or score 2 (at end of game one player is "OUT" which is read as 0.)
            score1 = int(p1_score_list[i][0])
            score2 = int(p2_score_list[i][0])
            delta_abs = abs(delta_score)
            # originally comparing if delta score = player value (thus one player out)
            # this was too unprecise. now checking if within 10
            game_end_indicator1 = abs(delta_abs-score1)
            game_end_indicator2 = abs(delta_abs-score2)
            if (game_end_indicator1 < 10) or (game_end_indicator2 < 10):
                break
            delta_score_list.append((int(p1_score_list[i][0] - p2_score_list[i][0]), p1_score_list[i][1]))

        if len(delta_score_list) == 0:
            no_game_img = cv2.imread("./assets/plots/default.png")
            cv2.imwrite("./assets/plots/cropped_new_plot.png", no_game_img)

            cur_time = ti.time()
            program_time = cur_time - start_time
            print(f"Data collection time: {int(program_time // 60)}:{int(program_time % 60)}")

            cap.release()
            cv2.destroyAllWindows()
            running = False
        else:
            # clean the list and remove wrong values (vals which are 5 times the previous one)
            threshold_factor = 5
            cleaned_delta_score_list = [delta_score_list[0]]
            for i in range(1, len(delta_score_list)):
                # remove big jumps
                if abs(delta_score_list[i][0] - delta_score_list[i - 1][0]) < threshold_factor * abs(delta_score_list[i - 1][0]):
                    cleaned_delta_score_list.append(delta_score_list[i])

            # plotting
            # Extracting scores and times from cleaned_delta_score_list
            scores = [pair[0] for pair in cleaned_delta_score_list]
            times_seconds = [pair[1] for pair in cleaned_delta_score_list]
            # fixing possible time deviation
            time_difference = int(total_duration_seconds - times_seconds[-1])
            extra_times = int(time_difference / sampling_frequency)
            final_time = times_seconds[-1]
            for i in range(extra_times):
                final_time += sampling_frequency
                times_seconds.append(final_time)
            for i in range(extra_times):
                scores.append(scores[-1])
            times_minutes = [time / 60 for time in times_seconds]

            final_points_list = scores      # save score list

            # set plot size
            width_pixels = 1000
            height_pixels = 360
            dpi = 100
            fig_width = width_pixels / dpi
            fig_height = height_pixels / dpi
            plt.figure(figsize=(fig_width, fig_height))

            # Create plot
            plt.plot(times_minutes, scores, marker=',', linestyle='-', color='Black')

            # background color
            plt.axhspan(0, max(scores), facecolor='lightblue', alpha=0.5)
            plt.axhspan(min(scores), 0, facecolor='red', alpha=0.5)

            # plt.xlabel('Time')
            # plt.ylabel('Score')
            plt.title('Score difference of Player1 to Player2')
            plt.grid(axis='y')
            plt.xlim(0, max(times_minutes))  # x axis limit

            # Function to format ticks as minutes and seconds
            def format_minutes(x, pos):
                minutes = int(x)
                seconds = int((x - minutes) * 60)
                return f"{minutes:02}:{seconds:02}"
            
            # custom tick formatter for x-axis
            plt.gca().xaxis.set_major_formatter(FuncFormatter(format_minutes))
            plt.savefig('./assets/plots/newPlot.png')

            # crop created plot
            new_plot = cv2.imread("./assets/plots/newPlot.png")
            new_plot_crop = new_plot[18:350, 40:940]  # y1:y2, x1:x2     with times
            cv2.imwrite("./assets/plots/cropped_new_plot.png", new_plot_crop)

            def format_seconds(seconds):
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                remaining_seconds = seconds % 60

                return f"{hours:01d}:{minutes:02d}:{remaining_seconds:02d}"

            def idle_vil_times():  # from - to
                prev_idle_vil_val = 0
                idle_vil_start_time = 0
                for value in idle_vil_list:
                    # print("idle vil:", (int(value[0]), int(value[1])))
                    if int(value[0]) > 0 and prev_idle_vil_val == 0:
                        idle_vil_start_time = int(value[1])
                    elif int(value[0]) == 0 and prev_idle_vil_val != 0:
                        time1 = format_seconds(idle_vil_start_time)
                        time2 = format_seconds(value[1])
                        idle_vil_times_list.append(str(time1 + " - " + time2))  # duration of idle villagers
                    prev_idle_vil_val = int(value[0])
            if show_idle_villager:
                idle_vil_times()

            def floating_ressources_times():  # from - to
                floating_res_start_time = 0
                started = False
                for i in range(len(food_list)):
                    # make sure to check only correctly read values (values with bad detection are set to sys.maxsize)
                    if (food_list[i][0] != sys.maxsize) and (wood_list[i][0] != sys.maxsize) and (coin_list[i][0] != sys.maxsize):
                        food = int(food_list[i][0])
                        wood = int(wood_list[i][0])
                        coin = int(coin_list[i][0])
                        total = food + wood + coin
                        if total >= 1500:      # total amount must be at least 1500. Checking percentages of "50 5 10" makes no sense
                            food_percentage = food/(total/100)
                            wood_percentage = wood/(total/100)
                            coin_percentage = coin/(total/100)
                            if (food_percentage >= 75) or (coin_percentage >= 75) or (wood_percentage >= 75):
                                if not started:
                                    floating_res_start_time = food_list[i][1]
                                    started = True
                            else:
                                if started:
                                    time1 = format_seconds(floating_res_start_time)
                                    time2 = format_seconds(food_list[i][1])
                                    floating_ressources_times_list.append(str(time1 + " - " + time2))  # note duration of floating ressources
                                    started = False
                        if total < 1500 and started:
                            time1 = format_seconds(floating_res_start_time)
                            time2 = format_seconds(food_list[i][1])
                            floating_ressources_times_list.append(str(time1 + " - " + time2))  # note duration of floating ressources
                            started = False
            if show_floating_ressources:
                floating_ressources_times()

            def get_vil_death_times():
                prev_count = 0
                for vil in vil_count_list:
                    current_count = vil[0]
                    if current_count < prev_count:
                        time = format_seconds(vil[1])
                        vil_death_times_list.append(time)
                    prev_count = current_count
            if show_villager_deaths:
                get_vil_death_times()

            def get_population_death_times():
                prev_pop = 0
                skip_count = 0
                for i, pop in enumerate(population_list):
                    if skip_count > 0:
                        if skip_count == 1:
                            prev_pop = int(pop[0])
                        skip_count -= 1
                    else:
                        current_pop = int(pop[0])
                        if current_pop < prev_pop:
                            time = format_seconds(pop[1])
                            population_death_times_list.append(time)
                            skip_count = (30 / sampling_frequency)  # if attack was found, skip 30 seconds before checking again
                        prev_pop = current_pop
            if show_attacks:
                get_population_death_times()

            # time of program
            cur_time = ti.time()
            program_time = cur_time - start_time
            print(f"Data collection time: {int(program_time // 60)}:{int(program_time % 60)}")

            # Release video capture and close windows
            cap.release()
            cv2.destroyAllWindows()
            running = False

def stop_running():
    global running
    running = False
    sys.exit()

