import numpy as np
from gnuradio import gr

class blk(gr.sync_block):
    """Embedded Python Block - Počet chýb, BER a počet bitov"""

    def __init__(self, processing=True):
        gr.sync_block.__init__(
            self,
            name='Errors-BER-Bits',
            in_sig=[np.byte, np.byte], # → blok má 2 vstupy (napr. vyslaný a prijatý signál).
            out_sig=[np.float32, np.float32, np.float32] # → má 3 výstupy (chyby, BER, celkové bity).
        )
        self.errors = 0
        self.total = 0
        self.processing = processing #– zapína/vypína spracovanie (ak False, blok nič nerobí)

    def work(self, input_items, output_items):
        if not self.processing:
            return len(output_items[0])

        in0, in1 = input_items[0], input_items[1]
        length = min(len(in0), len(in1))

        # XOR bajtov a rozbalenie na bity
        xor_vals = np.bitwise_xor(in0[:length], in1[:length]).astype(np.uint8)
        bit_errors = np.unpackbits(xor_vals).sum()

        self.errors += bit_errors
        self.total += length * 8  # každý bajt = 8 bitov

        ber = (self.errors / self.total) if self.total > 0 else 0.0

        # Zapíš rovnakú hodnotu do celého výstupného poľa
        output_items[0][:] = self.errors
        output_items[1][:] = ber
        output_items[2][:] = self.total

        return len(output_items[0])
