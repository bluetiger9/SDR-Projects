#!/usr/bin/python
#
#  ble-dump: SDR Bluetooth LE packet dumper
#
#  Copyright (C) 2016 Jan Wagner <mail@jwagner.eu>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#

from grc.gr_ble import gr_ble as gr_block
from grc.gr_ble_b205mini import gr_ble_b205mini as gr_bloc_b205mini
from optparse import OptionParser, OptionGroup
from gnuradio.eng_option import eng_option
from datetime import datetime, timedelta
from proto import *

# Print current Gnu Radio capture settings
def print_settings(gr, opts):
  print('\n ble-dump:  SDR Bluetooth LE packet dumper')
  print('\nCapture settings:')
  print(' Base Frequency {} Hz'.format(int(gr.get_ble_base_freq())))
  print(' Sample rate {} Hz'.format(int(gr.get_sample_rate())))
  print(' Squelch threshold {} dB'.format(int(gr.get_squelch_threshold())))

  print('\nLow-pass filter:')
  print(' Cutoff frequency {}'.format(int(gr.get_cutoff_freq())))
  print(' Transition width {}'.format(int(gr.get_transition_width())))

  print('\nGMSK demodulation:')
  print(' Samples per Symbol {}'.format(gr.get_gmsk_sps()))
  print(' Gain Mu {}'.format(gr.get_gmsk_gain_mu()))
  print(' Mu {}'.format(gr.get_gmsk_mu()))
  print(' Omega Limit {}'.format(gr.get_gmsk_omega_limit()))

  print('\nBluetooth LE:')
  print(' Scanning Channels {}'.format(opts.current_ble_channels.replace(',', ', ')))
  print(' Scanning Window {}'.format(opts.ble_scan_window))
  print(' Disable CRC check {}'.format(opts.disable_crc))
  print(' Disable De-Whitening {}'.format(opts.disable_dewhitening))

  print('PCAP output file {}'.format(opts.pcap_file))

# Setup Gnu Radio with defined command line arguments
def init_args(gr, opts):
  gr.set_sample_rate(int(opts.sample_rate))
  gr.set_squelch_threshold(int(opts.squelch_threshold))
  gr.set_cutoff_freq(int(opts.cutoff_freq))
  gr.set_transition_width(int(opts.transition_width))
  gr.set_gmsk_sps(opts.samples_per_symbol)
  gr.set_gmsk_gain_mu(opts.gain_mu)
  gr.set_gmsk_mu(opts.mu)
  gr.set_gmsk_omega_limit(opts.omega_limit)
  gr.set_ble_channel(int(opts.scan_channels[0]))

# Initialize command line arguments
def init_opts(gr):
  parser = OptionParser(option_class=eng_option, usage="%prog: [opts]")

  # Capture
  capture = OptionGroup(parser, 'Capture settings')
  capture.add_option("-i", "--in_file", type="string", default='', help="Input File")
  capture.add_option("-b", "--b205mini", type="string", default='', help="Use USRP B205mini-i")
  capture.add_option("-o", "--pcap_file", type="string", default='', help="PCAP output file or named pipe (FIFO)")
  capture.add_option("-m", "--min_buffer_size", type="int", default=65, help="Minimum buffer size [default=%default]")
  capture.add_option("-s", "--sample-rate", type="eng_float", default=gr.sample_rate, help="Sample rate [default=%default]")
  capture.add_option("-t", "--squelch_threshold", type="eng_float", default=gr.squelch_threshold, help="Squelch threshold (simple squelch) [default=%default]")

  # Low Pass filter
  filters = OptionGroup(parser, 'Low-pass filter:')
  filters.add_option("-C", "--cutoff_freq", type="eng_float", default=gr.cutoff_freq, help="Filter cutoff [default=%default]")
  filters.add_option("-T", "--transition_width", type="eng_float", default=gr.transition_width, help="Filter transition width [default=%default]")

  # GMSK demodulation
  gmsk = OptionGroup(parser, 'GMSK demodulation:')
  gmsk.add_option("-S", "--samples_per_symbol", type="eng_float", default=gr.gmsk_sps, help="Samples per symbol [default=%default]")
  gmsk.add_option("-G", "--gain_mu", type="eng_float", default=gr.gmsk_gain_mu, help="Gain mu [default=%default]")
  gmsk.add_option("-M", "--mu", type="eng_float", default=gr.gmsk_mu, help="Mu [default=%default]")
  gmsk.add_option("-O", "--omega_limit", type="eng_float", default=gr.gmsk_omega_limit, help="Omega limit [default=%default]")

  # Bluetooth L
  ble= OptionGroup(parser, 'Bluetooth LE:')
  ble.add_option("-c", "--current_ble_channels", type="string", default='37,38,39', help="BLE channels to scan [default=%default]")
  ble.add_option("-w", "--ble_scan_window", type="eng_float", default=10.24, help="BLE scan window [default=%default]")
  ble.add_option("-x", "--disable_crc", action="store_true", default=False, help="Disable CRC verification [default=%default]")
  ble.add_option("-y", "--disable_dewhitening", action="store_true", default=False, help="Disable De-Whitening [default=%default]")

  parser.add_option_group(capture)
  parser.add_option_group(filters)
  parser.add_option_group(gmsk)
  parser.add_option_group(ble)
  return parser.parse_args()

if __name__ == '__main__':
  MIN_BUFFER_LEN = 65

  # Initialize Gnu Radio
  gr_block = gr_block()
  
  # Initialize command line arguments
  (opts, args) = init_opts(gr_block)
  
  # use USRP B205mini-i ?
  if opts.b205mini:
    print("Using USRP B205mini-i.")
    gr_block = gr_block_b205mini()
  
  if opts.in_file:
    print("Reading from in file {}.", opts.in_file)
    infile = open_infile(opts.in_file)

  else:
    infile = None
    gr_block.start()

  if not opts.pcap_file:
    print('\nerror: please specify pcap output file (-p)')
    exit(1)

  # Verify BLE channels argument
  if ',' not in opts.current_ble_channels:
    opts.current_ble_channels += ','

  # Prepare BLE channels argument
  opts.scan_channels = [int(x) for x in opts.current_ble_channels.split(',')]

  # Set Gnu Radio opts
  init_args(gr_block, opts)

  # Print capture settings
  print_settings(gr_block, opts)

  # Open PCAP file descriptor
  pcap_fd = open_pcap(opts.pcap_file)

  current_hop = 1
  hopping_time = datetime.now() + timedelta(seconds=opts.ble_scan_window)

  # Set initial BLE channel
  current_ble_chan = opts.scan_channels[0]
  gr_block.set_ble_channel(BLE_CHANS[current_ble_chan])

  # Prepare Gnu Radio receive buffers
  gr_buffer = bytes() # ''
  lost_data = bytes() # ''

  print('Capturing on BLE channel [ {:d} ] @ {:d} MHz'.format(current_ble_chan, int(gr_block.get_freq() / 1000000)))

  try:
    while True:
      if not infile:
        # Move to the next BLE scanning channel
        if datetime.now() >= hopping_time:
          current_ble_chan = opts.scan_channels[current_hop % len(opts.scan_channels)]
          gr_block.set_ble_channel(BLE_CHANS[current_ble_chan])
          hopping_time = datetime.now() + timedelta(seconds=opts.ble_scan_window)
          current_hop +=1
          print('Switching to BLE channel [ {:d} ] @ {:d} MHz'.format(current_ble_chan, int(gr_block.get_freq() / 1000000)))

        # Fetch data from Gnu Radio message queue
        msg = gr_block.message_queue.delete_head()
        #print(msg)
        #print(str(msg.to_string()))
        gr_buffer += msg.to_string() #.decode("utf-8") 
        
      else:
        file_bytes = read_bytes(infile)
        if len(file_bytes) == 0:
          print("Reached end of file.")
          exit(0)
          
        gr_buffer += file_bytes
      
      print("Buf len {}".format(len(gr_buffer)))

      if len(gr_buffer) > opts.min_buffer_size:
        # Prepend lost data
        if len(lost_data) > 0:
          gr_buffer = lost_data + gr_buffer # ''.join(str(x) for x in lost_data) + gr_buffer
          lost_data = bytes()
          
        #print("Processing len {}".format(len(gr_buffer)))
        #print("Enum {} {} {} {}".format(BLE_PREAMBLE, type(BLE_PREAMBLE), ord(BLE_PREAMBLE), [position for position, byte, in enumerate(gr_buffer) if byte == ord(BLE_PREAMBLE)]))

        # Search for BLE_PREAMBLE in received data
        for pos in [position for position, byte, in enumerate(gr_buffer) if byte == ord(BLE_PREAMBLE)]:
          pos += BLE_PREAMBLE_LEN

          # Check enough data is available for parsing the BLE Access Address
          if len(gr_buffer[pos:]) < (BLE_ADDR_LEN + BLE_PDU_HDR_LEN):
            continue

          # Extract BLE Access Address
          ble_access_address = unpack('I', gr_buffer[pos:pos + BLE_ADDR_LEN])[0]
          print("BLE Access Address: {}".format(ble_access_address))
          pos += BLE_ADDR_LEN

          # Dewhitening received BLE Header
          if opts.disable_dewhitening == False:
            ble_header = dewhitening(gr_buffer[pos:pos + BLE_PDU_HDR_LEN], current_ble_chan)
          else:
            ble_header = gr_buffer[pos:pos + BLE_PDU_HDR_LEN]

          # Check BLE PDU type
          ble_pdu_type = ble_header[0] & 0x0f
          if ble_pdu_type not in BLE_PDU_TYPE.values():
             print("Not PDU Type: {}".format(ble_pdu_type))
             continue

          if ble_access_address == BLE_ACCESS_ADDR:
            # Extract BLE Length
            ble_len = ble_header[1] & 0x3f
          else:
            ble_llid = ble_header[0] & 0x3
            if ble_llid == 0:
              print("LLID=0")
              continue

            # Extract BLE Length
            ble_len = ble_header[1] & 0x1f

          # Dewhitening BLE packet
          if opts.disable_dewhitening == False:
            ble_data = dewhitening(gr_buffer[pos:pos + BLE_PDU_HDR_LEN + BLE_CRC_LEN + ble_len], current_ble_chan)
          else:
            ble_data = gr_buffer[pos:pos + BLE_PDU_HDR_LEN + BLE_CRC_LEN + ble_len]

          # Verify BLE data length
          if len(ble_data) != (BLE_PDU_HDR_LEN + BLE_CRC_LEN + ble_len):
            lost_data = gr_buffer[pos - BLE_PREAMBLE_LEN - BLE_ADDR_LEN:pos + BLE_PREAMBLE_LEN + BLE_ADDR_LEN + BLE_PDU_HDR_LEN + BLE_CRC_LEN + ble_len]
            print("Len loss.")
            continue

          # Verify BLE packet checksum
          if opts.disable_crc == False:
            if ble_data[-3:] != crc(ble_data, BLE_PDU_HDR_LEN + ble_len):
              print("CRC")
              continue

          # Write BLE packet to PCAP file descriptor
          write_pcap(pcap_fd, current_ble_chan, ble_access_address, ble_data)

        gr_buffer = bytes()

  except KeyboardInterrupt:
    pass

pcap_fd.close()
gr_block.stop()
gr_block.wait()
