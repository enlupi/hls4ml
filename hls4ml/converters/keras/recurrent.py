from hls4ml.converters.keras_to_hls import get_weights_data, keras_handler, parse_default_keras_layer

rnn_layers = ['SimpleRNN', 'LSTM', 'GRU']
merge_modes = ['sum', 'mul', 'concat', 'ave']


@keras_handler(*rnn_layers)
def parse_rnn_layer(keras_layer, input_names, input_shapes, data_reader):
    assert keras_layer['class_name'] in rnn_layers or keras_layer['class_name'][1:] in rnn_layers

    layer = parse_default_keras_layer(keras_layer, input_names)
    layer['direction'] = 'forward'

    layer['return_sequences'] = keras_layer['config']['return_sequences']
    layer['return_state'] = keras_layer['config']['return_state']

    if 'SimpleRNN' not in layer['class_name']:
        layer['recurrent_activation'] = keras_layer['config']['recurrent_activation']

    layer['time_major'] = keras_layer['config']['time_major'] if 'time_major' in keras_layer['config'] else False

    # TODO Should we handle time_major?
    if layer['time_major']:
        raise Exception('Time-major format is not supported by hls4ml')

    layer['n_timesteps'] = input_shapes[0][1]
    layer['n_in'] = input_shapes[0][2]

    layer['n_out'] = keras_layer['config']['units']

    layer['weight_data'], layer['recurrent_weight_data'], layer['bias_data'] = get_weights_data(
        data_reader, layer['name'], ['kernel', 'recurrent_kernel', 'bias']
    )

    if 'GRU' in layer['class_name']:
        layer['apply_reset_gate'] = 'after' if keras_layer['config']['reset_after'] else 'before'

        # biases array is actually a 2-dim array of arrays (bias + recurrent bias)
        # both arrays have shape: n_units * 3 (z, r, h_cand)
        biases = layer['bias_data']
        layer['bias_data'] = biases[0]
        layer['recurrent_bias_data'] = biases[1]

    if layer['return_sequences']:
        output_shape = [input_shapes[0][0], layer['n_timesteps'], layer['n_out']]
    else:
        output_shape = [input_shapes[0][0], layer['n_out']]

    if layer['return_state']:
        raise Exception('"return_state" of {} layer is not yet supported.')

    return layer, output_shape


@keras_handler('Bidirectional')
def parse_bidirectional_layer(keras_layer, input_names, input_shapes, data_reader):
    assert keras_layer['class_name'] == 'Bidirectional'

    rnn_layer = keras_layer['config']['layer']
    assert rnn_layer['class_name'] in rnn_layers or rnn_layer['class_name'][1:] in rnn_layers

    layer = parse_default_keras_layer(rnn_layer, input_names)
    layer['name'] = keras_layer['config']['name']
    layer['class_name'] = 'Bidirectional' + layer['class_name']
    layer['direction'] = 'bidirectional'

    # TODO Should we handle different architectures for forward and backward layer?
    if keras_layer['config'].get('backward_layer'):
        raise Exception('Different architectures between forward and backward layers are not supported by hls4ml')

    layer['return_sequences'] = rnn_layer['config']['return_sequences']
    layer['return_state'] = rnn_layer['config']['return_state']

    if 'SimpleRNN' not in layer['class_name']:
        layer['recurrent_activation'] = rnn_layer['config']['recurrent_activation']

    layer['time_major'] = rnn_layer['config']['time_major'] if 'time_major' in rnn_layer['config'] else False

    # TODO Should we handle time_major?
    if layer['time_major']:
        raise Exception('Time-major format is not supported by hls4ml')

    layer['n_timesteps'] = input_shapes[0][1]
    layer['n_in'] = input_shapes[0][2]

    assert keras_layer['config']['merge_mode'] in merge_modes
    layer['merge_mode'] = keras_layer['config']['merge_mode']

    layer['n_out'] = rnn_layer['config']['units']
    if keras_layer['config']['merge_mode'] == 'concat':
        layer['n_out'] *= 2

    rnn_layer_name = rnn_layer['config']['name']
    if 'SimpleRNN' in layer['class_name']:
        cell_name = 'simple_rnn'
    else:
        cell_name = rnn_layer['class_name'].lower()
    layer['weight_data'], layer['recurrent_weight_data'], layer['bias_data'] = get_weights_data(
        data_reader,
        layer['name'],
        [
            f'forward_{rnn_layer_name}/{cell_name}_cell/kernel',
            f'forward_{rnn_layer_name}/{cell_name}_cell/recurrent_kernel',
            f'forward_{rnn_layer_name}/{cell_name}_cell/bias',
        ],
    )
    layer['weight_b_data'], layer['recurrent_weight_b_data'], layer['bias_b_data'] = get_weights_data(
        data_reader,
        layer['name'],
        [
            f'backward_{rnn_layer_name}/{cell_name}_cell/kernel',
            f'backward_{rnn_layer_name}/{cell_name}_cell/recurrent_kernel',
            f'backward_{rnn_layer_name}/{cell_name}_cell/bias',
        ],
    )

    if 'GRU' in layer['class_name']:
        layer['apply_reset_gate'] = 'after' if rnn_layer['config']['reset_after'] else 'before'

        # biases array is actually a 2-dim array of arrays (bias + recurrent bias)
        # both arrays have shape: n_units * 3 (z, r, h_cand)
        biases = layer['bias_data']
        biases_b = layer['bias_b_data']
        layer['bias_data'] = biases[0]
        layer['recurrent_bias_data'] = biases[1]
        layer['bias_b_data'] = biases_b[0]
        layer['recurrent_bias_b_data'] = biases_b[1]

    if layer['return_sequences']:
        output_shape = [input_shapes[0][0], layer['n_timesteps'], layer['n_out']]
    else:
        output_shape = [input_shapes[0][0], layer['n_out']]

    if layer['return_state']:
        raise Exception('"return_state" of {} layer is not yet supported.')

    return layer, output_shape
