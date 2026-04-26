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
from gnuradio import analog
from gnuradio import blocks
import numpy
from gnuradio import channels
from gnuradio.filter import firdes
from gnuradio import digital
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
import Zapojenie_epy_block_0 as epy_block_0  # embedded python block
import Zapojenie_epy_block_0_0 as epy_block_0_0  # embedded python block
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
        self.samp_rate = samp_rate = 32000
        self.rcc_tabs = rcc_tabs = firdes.root_raised_cosine(nfilts, nfilts, 1.0/float(Samp_Symb), Excess_BW, 11*Samp_Symb*nfilts)
        self.phase = phase = 0
        self.gain = gain = 1.0
        self.eq_mu = eq_mu = 0.001
        self.Loop_Bandwidth = Loop_Bandwidth = 0.0628

        ##################################################
        # Blocks
        ##################################################

        self.epy_block_0_0 = epy_block_0_0.blk(example_param=0)
        self.epy_block_0 = epy_block_0.blk(example_param=0)
        self.digital_constellation_modulator_0 = digital.generic_mod(
            constellation=variable_constellation_0,
            differential=True,
            samples_per_symbol=Samp_Symb,
            pre_diff_code=True,
            excess_bw=Excess_BW,
            verbose=False,
            log=False,
            truncate=True)
        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(variable_constellation_0)
        self.channels_channel_model_0 = channels.channel_model(
            noise_voltage=0.1,
            frequency_offset=0.0,
            epsilon=1.0,
            taps=[1+0j],
            noise_seed=0,
            block_tags=False)
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.blocks_stream_to_tagged_stream_0 = blocks.stream_to_tagged_stream(gr.sizeof_char, 1, 336, "packet_len")
        self.blocks_rotator_cc_0 = blocks.rotator_cc(0.0, False)
        self.blocks_null_sink_1 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_null_sink_0 = blocks.null_sink(gr.sizeof_gr_complex*1)
        self.blocks_multiply_const_vxx_0 = blocks.multiply_const_cc(1)
        self.blocks_float_to_complex_1 = blocks.float_to_complex(1)
        self.blocks_float_to_complex_0 = blocks.float_to_complex(1)
        self.blocks_char_to_float_1 = blocks.char_to_float(1, 1)
        self.blocks_char_to_float_0 = blocks.char_to_float(1, 1)
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.analog_random_source_x_0 = blocks.vector_source_b(list(map(int, numpy.random.randint(0, 256, 100000))), True)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, 0.1, 0)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_noise_source_x_0, 0), (self.blocks_add_xx_0, 1))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_char_to_float_0, 0))
        self.connect((self.analog_random_source_x_0, 0), (self.blocks_stream_to_tagged_stream_0, 0))
        self.connect((self.blocks_add_xx_0, 0), (self.blocks_multiply_const_vxx_0, 0))
        self.connect((self.blocks_char_to_float_0, 0), (self.blocks_float_to_complex_0, 0))
        self.connect((self.blocks_char_to_float_1, 0), (self.blocks_float_to_complex_1, 0))
        self.connect((self.blocks_float_to_complex_0, 0), (self.epy_block_0, 0))
        self.connect((self.blocks_float_to_complex_1, 0), (self.epy_block_0_0, 0))
        self.connect((self.blocks_multiply_const_vxx_0, 0), (self.blocks_rotator_cc_0, 0))
        self.connect((self.blocks_rotator_cc_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.blocks_stream_to_tagged_stream_0, 0), (self.digital_constellation_modulator_0, 0))
        self.connect((self.blocks_throttle2_0, 0), (self.channels_channel_model_0, 0))
        self.connect((self.channels_channel_model_0, 0), (self.blocks_add_xx_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.blocks_char_to_float_1, 0))
        self.connect((self.digital_constellation_modulator_0, 0), (self.blocks_throttle2_0, 0))
        self.connect((self.epy_block_0, 0), (self.blocks_null_sink_1, 0))
        self.connect((self.epy_block_0_0, 0), (self.blocks_null_sink_0, 0))


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

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)

    def get_rcc_tabs(self):
        return self.rcc_tabs

    def set_rcc_tabs(self, rcc_tabs):
        self.rcc_tabs = rcc_tabs

    def get_phase(self):
        return self.phase

    def set_phase(self, phase):
        self.phase = phase

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain

    def get_eq_mu(self):
        return self.eq_mu

    def set_eq_mu(self, eq_mu):
        self.eq_mu = eq_mu

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
