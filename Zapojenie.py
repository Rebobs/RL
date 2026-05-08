#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Not titled yet
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
import numpy
from gnuradio import digital
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import Zapojenie_epy_block_0 as epy_block_0  # embedded python block
import Zapojenie_epy_block_0_0 as epy_block_0_0  # embedded python block
import sip
import threading



class Zapojenie(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Not titled yet", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Not titled yet")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "Zapojenie")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.nfilts = nfilts = 32
        self.Samp_Symb = Samp_Symb = 4
        self.Excess_BW = Excess_BW = 0.35
        self.variable_constellation_0 = variable_constellation_0 = digital.constellation_qpsk().base()
        self.variable_constellation_0.set_npwr(1.0)
        self.tx_delay = tx_delay = 0
        self.samp_rate = samp_rate = 1000000
        self.rcc_tabs = rcc_tabs = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(Samp_Symb), Excess_BW, 11*Samp_Symb*nfilts)
        self.phase = phase = 0
        self.noise_amp = noise_amp = 0.0
        self.gain = gain = 1.0
        self.eq_mu = eq_mu = 0.001
        self.amp_noise = amp_noise = 0.25
        self.Loop_Bandwidth = Loop_Bandwidth = 0.0628

        ##################################################
        # Blocks
        ##################################################

        self._amp_noise_range = qtgui.Range(0.01, 1, 0.01, 0.25, 200)
        self._amp_noise_win = qtgui.RangeWidget(self._amp_noise_range, self.set_amp_noise, "'amp_noise'", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._amp_noise_win)
        self.qtgui_time_sink_x_0 = qtgui.time_sink_f(
            1024, #size
            samp_rate, #samp_rate
            "", #name
            2, #number of inputs
            None # parent
        )
        self.qtgui_time_sink_x_0.set_update_time(1)
        self.qtgui_time_sink_x_0.set_y_axis(-1, 1)

        self.qtgui_time_sink_x_0.set_y_label('Amplitude', "")

        self.qtgui_time_sink_x_0.enable_tags(True)
        self.qtgui_time_sink_x_0.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.qtgui_time_sink_x_0.enable_autoscale(False)
        self.qtgui_time_sink_x_0.enable_grid(False)
        self.qtgui_time_sink_x_0.enable_axis_labels(True)
        self.qtgui_time_sink_x_0.enable_control_panel(False)
        self.qtgui_time_sink_x_0.enable_stem_plot(False)


        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                self.qtgui_time_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_time_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_time_sink_x_0.set_line_width(i, widths[i])
            self.qtgui_time_sink_x_0.set_line_color(i, colors[i])
            self.qtgui_time_sink_x_0.set_line_style(i, styles[i])
            self.qtgui_time_sink_x_0.set_line_marker(i, markers[i])
            self.qtgui_time_sink_x_0.set_line_alpha(i, alphas[i])

        self._qtgui_time_sink_x_0_win = sip.wrapinstance(self.qtgui_time_sink_x_0.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._qtgui_time_sink_x_0_win)
        self.qtgui_number_sink_0_0 = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_NONE,
            3,
            None # parent
        )
        self.qtgui_number_sink_0_0.set_update_time(0.10)
        self.qtgui_number_sink_0_0.set_title("Python BER")

        labels = ['Absolute Errors', 'My BER', 'Total Bits', '', '',
            '', '', '', '', '']
        units = ['errors', '= X', 'bits', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("blue", "red"), ("black", "white"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(3):
            self.qtgui_number_sink_0_0.set_min(i, 0)
            self.qtgui_number_sink_0_0.set_max(i, 1)
            self.qtgui_number_sink_0_0.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.qtgui_number_sink_0_0.set_label(i, "Data {0}".format(i))
            else:
                self.qtgui_number_sink_0_0.set_label(i, labels[i])
            self.qtgui_number_sink_0_0.set_unit(i, units[i])
            self.qtgui_number_sink_0_0.set_factor(i, factor[i])

        self.qtgui_number_sink_0_0.enable_autoscale(False)
        self._qtgui_number_sink_0_0_win = sip.wrapinstance(self.qtgui_number_sink_0_0.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._qtgui_number_sink_0_0_win, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.epy_block_0_0 = epy_block_0_0.blk(example_param=0)
        self.epy_block_0 = epy_block_0.blk(processing=True)
        self.digital_constellation_encoder_bc_0 = digital.constellation_encoder_bc(variable_constellation_0)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(variable_constellation_0)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_stream_to_tagged_stream_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, 336, "packet_len")
        self.blocks_rotator_cc_0 = blocks.rotator_cc(0.0, False)
        self.blocks_null_sink_1 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(2)
        self.blocks_float_to_complex_1 = blocks.float_to_complex(1)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_delay_tx = blocks.delay(gr.sizeof_char*1, tx_delay)
        self.blocks_char_to_float_1 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0 = blocks.char_to_float(1, 1)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 4, 100000))), True)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, amp_noise, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_char_to_float_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_delay_tx, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_stream_to_tagged_stream_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.epy_block_0, 1))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_char_to_float_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_char_to_float_0, 0), (self.qtgui_time_sink_x_0, 0))
        self.connect((self.blocks_char_to_float_1, 0), (self.blocks_float_to_complex_1, 0))
        self.connect((self.blocks_char_to_float_1, 0), (self.qtgui_time_sink_x_0, 1))
        self.connect((self.blocks_delay_tx, 0), (self.epy_block_0_0, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.blocks_null_sink_1, 0))
        self.connect((self.blocks_float_to_complex_1, 0), (self.blocks_null_sink_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_rotator_cc_0, 0))
        self.connect((self.blocks_rotator_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.digital_constellation_encoder_bc_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.epy_block_0_0, 1))
        self.connect((self.digital_constellation_encoder_bc_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.epy_block_0, 1), (self.qtgui_number_sink_0_0, 1))
        self.connect((self.epy_block_0, 2), (self.qtgui_number_sink_0_0, 2))
        self.connect((self.epy_block_0, 0), (self.qtgui_number_sink_0_0, 0))
        self.connect((self.epy_block_0_0, 0), (self.blocks_char_to_float_1, 0))
        self.connect((self.epy_block_0_0, 0), (self.epy_block_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "Zapojenie")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_rcc_tabs(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.Samp_Symb), self.Excess_BW, 11*self.Samp_Symb*self.nfilts))

    def get_Samp_Symb(self):
        return self.Samp_Symb

    def set_Samp_Symb(self, Samp_Symb):
        self.Samp_Symb = Samp_Symb
        self.set_rcc_tabs(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.Samp_Symb), self.Excess_BW, 11*self.Samp_Symb*self.nfilts))

    def get_Excess_BW(self):
        return self.Excess_BW

    def set_Excess_BW(self, Excess_BW):
        self.Excess_BW = Excess_BW
        self.set_rcc_tabs(firdes.root_raised_cosine(self.nfilts, self.nfilts, 1.0/float(self.Samp_Symb), self.Excess_BW, 11*self.Samp_Symb*self.nfilts))

    def get_variable_constellation_0(self):
        return self.variable_constellation_0

    def set_variable_constellation_0(self, variable_constellation_0):
        self.variable_constellation_0 = variable_constellation_0
        self.digital_constellation_decoder_cb_0.set_constellation(self.variable_constellation_0)
        self.digital_constellation_encoder_bc_0.set_constellation(self.variable_constellation_0)

    def get_tx_delay(self):
        return self.tx_delay

    def set_tx_delay(self, tx_delay):
        self.tx_delay = tx_delay
        self.blocks_delay_tx.set_dly(int(self.tx_delay))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)
        self.qtgui_time_sink_x_0.set_samp_rate(self.samp_rate)

    def get_rcc_tabs(self):
        return self.rcc_tabs

    def set_rcc_tabs(self, rcc_tabs):
        self.rcc_tabs = rcc_tabs

    def get_phase(self):
        return self.phase

    def set_phase(self, phase):
        self.phase = phase

    def get_noise_amp(self):
        return self.noise_amp

    def set_noise_amp(self, noise_amp):
        self.noise_amp = noise_amp

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain

    def get_eq_mu(self):
        return self.eq_mu

    def set_eq_mu(self, eq_mu):
        self.eq_mu = eq_mu

    def get_amp_noise(self):
        return self.amp_noise

    def set_amp_noise(self, amp_noise):
        self.amp_noise = amp_noise
        self.analog_noise_source_x_0.set_amplitude(self.amp_noise)

    def get_Loop_Bandwidth(self):
        return self.Loop_Bandwidth

    def set_Loop_Bandwidth(self, Loop_Bandwidth):
        self.Loop_Bandwidth = Loop_Bandwidth




def main(top_block_cls=Zapojenie, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
