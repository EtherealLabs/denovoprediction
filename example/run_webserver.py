from os.path import dirname, abspath
import sys
from multiprocessing import Process, Queue

import time
from gevent.wsgi import WSGIServer
from celery import Celery

par_path = dirname(dirname(abspath(__file__)))
sys.path.append(par_path)

from flask import Flask, jsonify, render_template, send_from_directory, request, url_for
from src.pipeline.Pipeline import *
import threading
import os

project_root = os.path.dirname(__file__)
app = Flask(__name__, template_folder=project_root, static_url_path='/static')
app.debug = True

# Celery configuration
app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

# Initialize Celery
celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)

global pipeline
global thread


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/gen/current')
def get_current_conformation():
    global pipeline
    if pipeline is None:
        return jsonify(result={"status": 400})
    if pipeline.get_current_conformation() is None:
        return jsonify(result={"status": 202})

    pdb = map_conformation_to_pdb(pipeline.get_current_conformation(), app.static_folder, True)

    # pdb = "trythis.pdb"
    # print "Sending Conformation Upon Request"
    return send_from_directory(app.static_folder, os.path.basename(pdb))


@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = generate_conformation.AsyncResult(task_id)
    # print task.state
    #if task.state == "NEXT":
     #   return jsonify({"current": task.info["current"],
     #                   "total": task.info["total"]})
    if task.state == "PDB_CHANGE":
        return send_from_directory(app.static_folder, os.path.basename(task.info["pdb"]))

    return jsonify({"status": task.state})


@app.route('/generate', methods=["POST"])
def generate():
    name = request.form["sequence"]
    casp_info = get_casp_info(name)
    robetta_dict = casp_info["fragments"]
    sequence = casp_info["sequence"]

    task = generate_conformation.apply_async((name, robetta_dict, sequence))

    return jsonify({}), 202, {'Location': url_for('taskstatus', task_id=task.id)}


@celery.task(bind=True)
def generate_conformation(self, name, robetta_dict, sequence):
    """Background task that runs to generate the Conformation with frequent
    updates in the form of PDB files and other data"""
    global pipeline
    # pipeline = LinearPipeline(name, sequence, robetta_dict)
    new_dict = {}
    for key in robetta_dict:
        new_dict[int(key)] = robetta_dict[key]
    frag_lib = RobettaFragmentLibrary(sequence)
    frag_lib.generate(new_dict)
    seef = DFirePotential()
    self.conformation = LinearBackboneConformation(name, sequence)
    self.conformation.initialize()
    sampler = ConformationSampler(self.conformation, seef, frag_lib, app.static_folder)

    count = 0

    while sampler.has_next():
        old_pdb = self.conformation.get_pdb_file()
        self.conformation = sampler.next_conformation()
        new_pdb = self.conformation.get_pdb_file()

        self.update_state(state="NEXT",
                          meta={"current": count,
                                "total": sampler.get_k_max()})
        count += 1
        if old_pdb != new_pdb:
            self.update_state(state="PDB_CHANGE",
                              meta={"pdb": self.conformation.get_pdb_file()})

            # TODO submit to 3dmol.js

    self.conformation = sampler.minimum()
    self.update_state(state="PDB_FINAL",
                      meta={"pdb": self.conformation.get_pdb_file()})

    print "%%%%%%%%%%%%%%%%%%%%% FINAL %%%%%%%%%%%%%%%%%%%%%"
    print self.conformation.get_pdb_file()

    # print "Beginning while loop"
    # while pipeline.is_complete():
    #     if random.random() < 0.10:
    #         self.update_state(state="PROGRESS",
    #                           meta={'complete': pipeline.is_complete(),
    #                                 'pdb':  pipeline.get_current_conformation().get_pdb_file()})
    #          time.sleep(1)
    return {"status": 200}


"""@app.route('/gen', methods=["POST"])
def gen():
    print "Beginning De Novo Generation"
    data = request.form["sequence"]
    casp_info = get_casp_info(data)
    robetta_dict = casp_info['fragments']
    sequence = casp_info['sequence']
    experimental_pdb = casp_info['experimental_pdb']
    global pipeline
    global thread
    pipeline = LinearPipeline(data, sequence, robetta_dict, experimental_pdb)
    # thread = threading.Thread(target=pipeline.generate_structure_prediction(app.static_folder))
    # thread.start()

    # run_de_novo()
    return jsonify(result={"status": 200})


@app.route('/gen/complete')
def is_done():
    global pipeline
    if pipeline is None:
        return jsonify(result={"status": 400})

    return jsonify(complete=pipeline.is_complete())"""

casp_dict = {
    'casp10_t0678': {
        'root': 'CASP10_T0678_UP20725R',
        'sequence': '',
        'fragments': '',
        'expPDB': '4epz.pdb', 
        'experimental_pdb': ''
    },
    'casp10_t0651': {
        'root': 'CASP10_T0651_LGR82',
        'sequence': '',
        'fragments': '',
        'expPDB': '4f67.pdb',
        'experimental_pdb': ''
    },
    'casp10_t0694': {
        'root': 'CASP10_T0694_APC100075',
        'sequence': '',
        'fragments': '',
        'expPDB': '5jh8.pdb',
        'experimental_pdb': ''
    },
    'casp10_t0757': {
        'root': 'CASP10_T0757_APC103790',
        'sequence': '',
        'fragments': '',
        'expPDB': '4gak.pdb',
        'experimental_pdb': ''
    },
    'casp10_t0666': {
        'root': 'CASP10_T0666_UCI_BBCS',
        'sequence': '',
        'fragments': '',
        'expPDB': '3ux4.pdb',
        'experimental_pdb': ''
    },
    'casp11_t0837': {
        'root': 'CASP11_T0837_YPO2654',
        'sequence': '',
        'fragments': '',
        'expPDB': '5tf3.pdb',
        'experimental_pdb': ''
    },
    'casp11_t0792': {
        'root': 'CASP11_T0792_Oskar-N',
        'sequence': '',
        'fragments': '',
        'expPDB': '5a49.pdb',
        'experimental_pdb': ''
    },
    'casp11_t0806': {
        'root': 'CASP11_T0806_YaaA',
        'sequence': '',
        'fragments': '',
        'expPDB': '5caj.pdb',
        'experimental_pdb': ''
    },
    'casp11_t0843': {
        'root': 'CASP11_T0843_Ats13',
        'sequence': '',
        'fragments': '',
        'expPDB': '4xau.pdb',
        'experimental_pdb': ''
    },
    'casp11_t0856': {
        'root': 'CASP11_T0856_HERC1',
        'sequence': '',
        'fragments': '',
        'expPDB': '4qt6.pdb',
        'experimental_pdb': ''
    }
}


def get_casp_info(casp_name):
    seq = ''
    path3mer = os.path.join(app.static_folder, casp_dict[casp_name]['root'], 'aat000_03_05.200_v1_3.txt')
    path9mer = os.path.join(app.static_folder, casp_dict[casp_name]['root'], 'aat000_09_05.200_v1_3.txt')
    path_fasta = os.path.join(app.static_folder, casp_dict[casp_name]['root'], 't000_.fasta')
    path_exp = os.path.join(app.static_folder, 'ExperimentalNativeStructures', casp_dict[casp_name]['root'], casp_dict[casp_name]['expPDB'])
    with open(path_fasta) as fasta:
        next(fasta)
        for line in fasta:
            seq += line[:-1]  # remove newline char
    return {
        'sequence': seq,
        'fragments': {
            3: path3mer,
            9: path9mer
        },
        'experimental_pdb': path_exp
    }
    
if __name__ == "__main__":
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
    # app.run(debug=True, threaded=True)
