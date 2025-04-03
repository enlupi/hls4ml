import numpy as np

from hls4ml.converters.keras_to_hls import get_weights_data, keras_handler, parse_default_keras_layer

rnn_layers = ['SimpleRNN', 'LSTM', 'GRU']


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
    layer['direction'] = 'bidirectional'

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

    layer['n_out'] = 2*rnn_layer['config']['units']


    if 'SimpleRNN' in layer['class_name']:
        cell_name = 'simple_rnn'
    else:
        cell_name = layer['class_name'].lower()
    weight_data_f, recurrent_weight_data_f, bias_data_f = get_weights_data(
        data_reader, layer['name'], [f'forward_{cell_name}/{cell_name}_cell/kernel',
                                     f'forward_{cell_name}/{cell_name}_cell/recurrent_kernel', 
                                     f'forward_{cell_name}/{cell_name}_cell/bias']
    )
    weight_data_b, recurrent_weight_data_b, bias_data_b = get_weights_data(
        data_reader, layer['name'], [f'backward_{cell_name}/{cell_name}_cell/kernel',
                                     f'backward_{cell_name}/{cell_name}_cell/recurrent_kernel', 
                                     f'backward_{cell_name}/{cell_name}_cell/bias']
    )
    layer['weight_data'] = np.stack((weight_data_f, weight_data_b), axis=0)
    layer['recurrent_weight_data'] = np.stack((recurrent_weight_data_f, recurrent_weight_data_b), axis=0)
    layer['bias_data'] = np.stack((bias_data_f, bias_data_b), axis=0)

    if 'GRU' in layer['class_name']:
        layer['apply_reset_gate'] = 'after' if rnn_layer['config']['reset_after'] else 'before'

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
