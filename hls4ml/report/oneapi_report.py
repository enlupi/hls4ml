import glob
import os
import json
import re


def convert_to_oneapi_naming(s):
    s2 = s.lower()

    # Capitalize the first letter
    s2 = s.capitalize()
    
    # Capitalize letters after numbers and underscores, and remove underscores
    s2 = re.sub(r'(_|\d)([a-z])', lambda m: m.group(1) + m.group(2).upper(), s2)
    
    # Remove underscores
    s2 = s2.replace('_', '')
    
    return s2


def parse_oneapi_report(prjDir):
    
    if not os.path.exists(prjDir):
        print(f'Path {prjDir} does not exist. Exiting.')
        return
    
    report = {}

    PathJson = prjDir + "/reports/resources/json/"
    PathQuartusJson = PathJson + "quartus.ndjson"
    PathHLSJson = PathJson + "area.ndjson"
    #PathInfoJson = PathJson + "info.ndjson"
    #PathSimDataJson = PathJson + "simulation_raw.ndjson"

    targetName, makeType, _ = os.path.basename(prjDir).rsplit(".", 2)
    simTask = convert_to_oneapi_naming(targetName)
    #if targetName not in report:
    #    report[targetName] = {}

    # you will probably need to modify this section if you compile a design with
    # multiple HLS components.
    if not os.path.exists(PathQuartusJson) or not os.path.exists(PathHLSJson):
        print(f'Unable to read project data. Exiting.')
        return

    with open(PathQuartusJson, 'r') as fileQuartusData:
        JsonDataQuartus = json.load(fileQuartusData)
    with open(PathHLSJson, 'r') as fileHLSData:
        JsonDataHLS = []
        for line in fileHLSData:
            JsonDataHLS.append(json.loads(line))           
    #with open(PathInfoJson, 'r') as fileInfo:
    #    JsonInfo = json.load(fileInfo)
    #simTask = str(JsonInfo["compileInfo"]["nodes"][0]["name"])

    # read synthesis info in quartus.ndjson 
    if makeType == "fpga":
        quartusReport = {}  

        componentNode = -1
        for nodeIdx in range(len(JsonDataQuartus["quartusFitResourceUsageSummary"]["nodes"])):
            if JsonDataQuartus["quartusFitResourceUsageSummary"]["nodes"][nodeIdx]["name"] == simTask:
                componentNode = nodeIdx
        if componentNode == -1:
            componentNode = 0
            print("Could not find component named %s in quartus data. use component %s instead." % (simTask, JsonDataQuartus["quartusFitResourceUsageSummary"]["nodes"][componentNode]["name"]))   
        
        quartusReport["fmax"] = JsonDataQuartus["quartusFitClockSummary"]["nodes"][0]["clock fmax"]
        resourcesList = ["alm", "alut", "reg", "dsp", "ram", "mlab"]
        for resource in resourcesList:
            quartusReport[resource] = JsonDataQuartus["quartusFitResourceUsageSummary"]["nodes"][componentNode][resource]
    
        report["Quartus"] = quartusReport

    # read HLS info in area.ndjson
    hlsReport = {}
    hlsReport["total"] = {}
    hlsReport["available"] = {}
    resourcesList = ["alut", "reg", "ram", "dsp", "mlab"]
    for i_resource, resource in enumerate(resourcesList):
        hlsReport["total"][resource] = JsonDataHLS[0]["total"][i_resource]
        hlsReport["available"][resource] = JsonDataHLS[0]["max_resources"][i_resource]

    report["HLS"] = hlsReport
             
    return report


def print_oneapi_report(report_dict):
    if _is_running_in_notebook():
        _print_ipython_report(report_dict)
    else:
        _print_str_report(report_dict)

def _print_ipython_report(report_dict):
    from IPython.display import HTML, display

    html = '<html>\n' + _table_css + '<div class="hls4ml">'
    body = _make_report_body(report_dict, _make_html_table_template, _make_html_header)
    html += body + '\n</div>\n</html>'
    display(HTML(html))

def _print_str_report(report_dict):
    body = _make_report_body(report_dict, _make_str_table_template, _make_str_header)
    print(body)

def _is_running_in_notebook():
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True  # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter

_table_css = """
<style>
.hls4ml {
    font-family: Tahoma, Geneva, sans-serif;
}
.hls4ml h3 {
    font-size: 15px;
    font-weight: 600;
    color: #54585d;
}
.hls4ml table {
    border-collapse: collapse;
    display: inline-block;
    padding: 2px;
}
.hls4ml table td {
    text-align: right;
    padding: 10px;
}
.hls4ml table td:nth-child(1) {
    text-align: left;
}
.hls4ml table thead td {
    background-color: #54585d;
    color: #ffffff;
    font-weight: bold;
    font-size: 11px;
    border: 1px solid #54585d;
}
.hls4ml table tbody td {
    color: #636363;
    border: 1px solid #dddfe1;
    font-size: 11px;
}
.hls4ml table tbody tr {
    background-color: #f9fafb;
}
.hls4ml table tbody tr:nth-child(odd) {
    background-color: #ffffff;
}
</style>
"""

_table_base_template = """
<table>
    <thead>
        <tr>
        <td colspan={colspan}>{table_header}</td>
        </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
</table>
"""

def _make_html_table_template(table_header, row_templates):

    num_columns = len(next(iter(row_templates.values())))

    _row_html_template = "        <tr><td>{row_title}</td>" + \
                         "".join("<td>{{{}}}</td>" for _ in range(num_columns)) + "</tr>"

    table_rows = '\n'.join(
        [_row_html_template.format(row_title=row_title, *row_keys) for row_title, row_keys in row_templates.items()]
    )
    return _table_base_template.format(colspan=num_columns+1, table_header=table_header, table_rows=table_rows)

def _make_str_table_template(table_header, row_templates):

    len_title = 0
    for row_title in row_templates.keys():
        if len(row_title) > len_title:
            len_title = len(row_title)

    head = f'\n - {table_header}:\n'
    table_rows = '\n'.join(
        ['    ' + f'{row_title}:'.ljust(len_title + 2) + "".join(f" {{{entry}:<17}}" for entry in row_keys) \
                                                                                     for row_title, row_keys in row_templates.items()]
    )
    
    return head + table_rows + '\n'

def _make_html_header(report_header):
    return f'<h3>{report_header}:</h3>'


def _make_str_header(report_header):
    sep = '=' * 54 + '\n'
    return '\n' + sep + '== ' + report_header + '\n' + sep
    

def _get_percentage(part, total):
    percentage = round(part / total * 100, 1)
    if percentage >= 0.1:
        return ' (' + str(percentage) + '%)'
    else:
        return ' (< 0.1%)'


def _make_report_body(report_dict, make_table_template, make_header_template):
    body = ''

    perf_rows = {}
    area_rows = {
        "":      ["hls",      "avail"],
        "ALUTs": ["alut_hls", "alut_avail"],
        "FFs":   ["reg_hls",  "reg_avail"],
        "DSPs":  ["dsp_hls",  "dsp_avail"],
        "RAMs":  ["ram_hls",  "ram_avail"],
        "MLABs": ["mlab_hls", "mlab_avail"]
    }

    if "Quartus" not in report_dict:
        body += make_header_template('FPGA HLS')
    else:
        body += make_header_template('FPGA Hardware Synthesis')

        perf_rows = {
            'Maximum Frequency': ['fmax']
                #'Best-case latency': 'best_latency',
                #'Worst-case latency': 'worst_latency',
                #'Interval Min': 'interval_min',
                #'Interval Max': 'interval_max',
                #'Estimated Clock Period': 'estimated_clock',
        }

        area_rows["ALMs" ] = ["alm_quartus", "alm_hls", "alm_avail"]
        area_rows[""].insert(0, "quartus")
        area_rows["ALUTs"].insert(0, "alut_quartus")
        area_rows["FFs"  ].insert(0, "reg_quartus")
        area_rows["DSPs" ].insert(0, "dsp_quartus")
        area_rows["RAMs" ].insert(0, "ram_quartus")
        area_rows["MLABs"].insert(0, "mlab_quartus")
        
        body += make_table_template('Performance estimates', perf_rows)
    body += make_table_template('Resource estimates', area_rows)

    params = {}
    params["hls"] = "HLS Estimation"
    params["avail"] = "Available"
    resourcesList = ["alut", "reg", "ram", "dsp", "mlab"]
    for resource in resourcesList:
        resource_hls   = int(report_dict["HLS"]["total"][resource])
        resource_avail = int(report_dict["HLS"]["available"][resource])
        params[resource+"_hls"] = str(resource_hls) + _get_percentage(resource_hls, resource_avail)
        params[resource+"_avail"] = str(resource_avail)
        if "Quartus" in report_dict:
            resource_quartus = int(report_dict["Quartus"][resource])
            params[resource+"_quartus"] = str(resource_quartus) + _get_percentage(resource_quartus, resource_avail)
    
    if "Quartus" in report_dict:
        params["quartus"] = "Quartus Synthesis"
        params["fmax"] = report_dict["Quartus"]['fmax']
        params["alm_quartus"] = report_dict["Quartus"]["alm"]
        params["alm_hls"] = "N/A"
        params["alm_avail"] = "N/A"

    body = body.format(**params)

    return body