import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.chart import ScatterChart, Reference, Series
import os
import tkinter as tk
from tkinter import messagebox

def get_num_signal(df):
    num_signal = df.shape[1] - 1
    return num_signal

def get_sample_length(df):
    sample_length = df.shape[0] - 1
    return sample_length

def get_signal_name(df):
    signal_name_list = []
    for i in range(0, get_num_signal(df) + 1):
        signal_name = df.iloc[0, i]
        signal_name_list.append(signal_name)
    return signal_name_list

def get_signal_data(df):
    signal_list = []
    for i in range(0, get_num_signal(df)+1):
        signal = df.iloc[1:, i].tolist()
        signal_list.append(signal)
    return signal_list

def get_file_type(file_path):
    if '.' in file_path:
        return file_path.rsplit('.', 1)[-1]
    return "No extension"

def get_file_name(file_path):
    filename_with_extension = os.path.basename(file_path)
    filename_without_extension = os.path.splitext(filename_with_extension)[0]
    return filename_without_extension

def get_user_inputs():
    root = tk.Tk()
    root.title("Settings")

    def submit_inputs():
        nonlocal unit, sample_rate, file_path
        unit = unit_entry.get() or default_unit
        sample_rate_input = sample_rate_entry.get()
        file_path = file_path_entry.get() or default_file_path

        sample_rate = int(sample_rate_input) if sample_rate_input else default_sample_rate
        # try:
        #     sample_rate = int(sample_rate_input) if sample_rate_input else default_sample_rate
        # except ValueError:
        #     messagebox.showerror("Error", "Sample rate must be an integer.")
        #     return

        root.destroy()

    unit = default_unit
    sample_rate = default_sample_rate
    file_path = default_file_path

    # tk.Label(root, text="This program can only accept .xlsx, .dat, .csv and .txt file.").pack()
    tk.Label(root, text="This program can only accept .xlsx file.").pack()
    tk.Label(root, text="Enter unit (default: cnt):").pack()
    unit_entry = tk.Entry(root)
    unit_entry.pack()

    tk.Label(root, text="Enter sample rate (default: 16000):").pack()
    sample_rate_entry = tk.Entry(root)
    sample_rate_entry.pack()

    tk.Label(root, text="Enter file path (default: measured_signal.xlsx):").pack()
    file_path_entry = tk.Entry(root)
    file_path_entry.pack()

    submit_button = tk.Button(root, text="Submit", command=submit_inputs)
    submit_button.pack()

    root.mainloop()

    return unit, sample_rate, file_path

default_file_path='measured_signal.xlsx'
default_unit = "cnt"
default_sample_rate = 16000

unit, sample_rate, file_path = get_user_inputs()

#file_type = get_file_type(file_path)
file_type = "xlsx"
file_name = get_file_name(file_path)
file_path = file_path + ".xlsx"

if file_type == "xlsx":
    excel_file = pd.ExcelFile(file_path)
else:
    raise ValueError("Unsupported file type. Please provide an .xlsx file.")

fft_vals_norm_all_sheets = []
fft_freq_all_sheets = []
fft_phase_all_sheets = []
fft_vals_db_all_sheets = []
fft_vals_cpk_all_sheets = []

for sheet_name in excel_file.sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)


    num_signal = get_num_signal(df)
    sample_length = get_sample_length(df)
    signal_name_list = get_signal_name(df)
    signal_data_list = get_signal_data(df)

    fft_vals_norm_all = []
    fft_freq_all = []
    fft_phase_all = []
    fft_vals_db_all = []
    fft_vals_cpk_all = []


    for i in range(num_signal+1):

        #signal[i]=(2.5-signal/256/8388608*2.5)/5*0.0005*1000000
        # for x in range(0, sample_length):
        #     if float(signal_data_list[i][x])>32767:
        #         signal_data_list[i][x]=float(signal_data_list[i][x])-65536
        #         signal_data_list[i][x] = str(signal_data_list[i][x])
        #     else:
        #         signal_data_list[i][x]=str(signal_data_list[i][x])

        fft_vals = np.fft.rfft(signal_data_list[i])
        fft_vals_norm = np.abs(fft_vals) / sample_length * (2 ** 0.5)
        fft_vals_norm[0] /= (2 ** 0.5)
        fft_vals_db = 20 * np.log10(fft_vals_norm)
        fft_phase = np.degrees(np.angle(fft_vals))

        fft_vals_cpk = np.zeros(get_sample_length(fft_vals_norm)+1)
        for j in range(get_sample_length(fft_vals_norm)):
            fft_vals_cpk[j+1] = (fft_vals_norm[j+1]**2 + fft_vals_cpk[j]**2)**0.5

        fft_vals_norm_all.append(fft_vals_norm)
        fft_vals_db_all.append(fft_vals_db)
        fft_phase_all.append(fft_phase)
        fft_vals_cpk_all.append(fft_vals_cpk)

        fft_freq = np.fft.rfftfreq(sample_length, 1.0 / sample_rate)
        fft_freq_all.append(fft_freq)

    fft_vals_norm_all_sheets.append(fft_vals_norm_all)
    fft_freq_all_sheets.append(fft_freq_all)
    fft_phase_all_sheets.append(fft_phase_all)
    fft_vals_db_all_sheets.append(fft_vals_db_all)
    fft_vals_cpk_all_sheets.append(fft_vals_cpk_all)

# for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
#     fig, axs = plt.subplots(num_signal, 3, figsize=(15, 5 * num_signal), constrained_layout=True)
#
#     for i in range(num_signal):
#         col = 0
#         row = i
#
#         axs[row, col].plot(fft_freq_all_sheets[sheet_index][i], fft_vals_norm_all_sheets[sheet_index][i])
#         axs[row, col].set_title(f"Frequency Spectrum {i + 1} ({unit})")
#         axs[row, col].set_xlabel("Frequency (Hz)")
#         axs[row, col].set_ylabel(f"Magnitude ({unit})")
#         axs[row, col].grid(True)
#
#         axs[row, col + 1].plot(fft_freq_all_sheets[sheet_index][i], fft_phase_all_sheets[sheet_index][i])
#         axs[row, col + 1].set_title(f"Phase vs Freq {i + 1}")
#         axs[row, col + 1].set_xlabel('Frequency (Hz)')
#         axs[row, col + 1].set_ylabel('Phase (degree)')
#         axs[row, col + 1].set_yticks(np.logspace(-2, 2, num=5), minor=True)
#         axs[row, col + 1].grid(True, which='both')
#
#         axs[row, col + 2].plot(fft_freq_all_sheets[sheet_index][i], fft_vals_db_all_sheets[sheet_index][i])
#         axs[row, col + 2].set_title(f"Frequency Spectrum {i + 1} (dB)")
#         axs[row, col + 2].set_xlabel('Frequency (Hz)')
#         axs[row, col + 2].set_ylabel('Magnitude (dB)')
#         axs[row, col + 2].grid(True)
#
# plt.show()

output_file_base_name = file_name + '_fft.xlsx'
output_file_writer = pd.ExcelWriter(output_file_base_name, engine='openpyxl')

for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
    data = pd.DataFrame({'Frequency (Hz)': fft_freq_all_sheets[sheet_index][0]})

    for i in range(num_signal+1):
        mag_V = str(signal_name_list[i]) + f"_Mag ({unit})"
        #mag_dB = str(signal_name_list[i]) + "_Magnitude (dB)"
        phase = str(signal_name_list[i]) + "_Phase (deg)"
        mag_cpk_V = str(signal_name_list[i]) + f"_Mag_CPK ({unit})"

        data[mag_V] = fft_vals_norm_all_sheets[sheet_index][i]
        #data[mag_dB] = fft_vals_db_all_sheets[sheet_index][i]
        data[mag_cpk_V] = fft_vals_cpk_all_sheets[sheet_index][i]
        data[phase] = fft_phase_all_sheets[sheet_index][i]

    data.to_excel(output_file_writer, sheet_name=sheet_name, index=False)

output_file_writer._save()

workbook = openpyxl.load_workbook(output_file_base_name)

for sheet_index, sheet_name in enumerate(excel_file.sheet_names):
    sheet = workbook[sheet_name]

#    for i in range(1, num_signal + 1):
#        chart = ScatterChart()
#        x_values = Reference(sheet, min_col=1, min_row=2, max_row=len(fft_freq_all_sheets[sheet_index][i - 1]) + 1)
#        values = Reference(sheet, min_col=i + 2 + 2 * (i - 1)-1, min_row=2, max_row=len(fft_vals_norm_all_sheets[sheet_index][i - 1]) + 1)
#        series = Series(values, x_values, title=signal_name_list[i - 1])
#        chart.series.append(series)
#        chart.x_axis.title = "Frequency (Hz)"
#        chart.y_axis.title = f"Magnitude ({unit})"
#        chart.x_axis.scaling.max = sample_rate / 2
#        chart.title = f"Magnitude ({unit})"
#        chart.legend.position = 't'
#        sheet.add_chart(chart, f"O{16 * (i - 1) + 1}")

workbook.save(output_file_base_name)
