# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Layer2Triple
                                 A QGIS plugin
 Layer2Triple
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-04-03
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Sergio Costa
        email                : sergio.costa@ufma.br
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from PyQt5.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction, QTableWidgetItem, QTableWidget, QCheckBox, QComboBox, QLineEdit, QFileDialog,QProgressDialog,QGroupBox,QVBoxLayout,QHBoxLayout,QPushButton,QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer, QgsRasterLayer,   QgsMultiPolygon,QgsMessageLog,QgsTask, QgsApplication

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .Layer2Triple_main import Layer2TripleMain
from .VocabularyDialog import VocabularyDialog
import os.path


import uuid 

from functools import partial

import re

from rdflib import Namespace, Literal, URIRef,RDF, Graph

from rdflib.namespace import DC, FOAF


import json


 
settings = {

    "TRIPLEPREFIX" : "obs",
    "TRIPLEURL" : "https://purl.org/dbcells/observation#",
    "TRIPLETYPE" : "qb:Observation",

    "NAMESPACES" : {
        #'dbc': (Namespace("http://www.purl.org/linked-data/dbcells#"), 'ttl'),
        #'geo' : (Namespace ("http://www.opengis.net/ont/geosparql"), 'xml'),
        #'sdmx' : (Namespace ("http://purl.org/linked-data/sdmx/2009/dimension#"), 'ttl'),
        #'dbc-attribute' : (Namespace ("http://www.purl.org/linked-data/dbcells/attribute#"), "ttl"),
        #'dbc-measure' : (Namespace ("http://www.purl.org/linked-data/dbcells/measure#"), "ttl"),
        #'dbc-code' : (Namespace ("http://www.purl.org/linked-data/dbcells/code#"), "ttl"),
        #'qb' : (Namespace ("http://purl.org/linked-data/cube#"), "ttl")
    }
 }

# depois vou remover essa variavel, evitar isso
namespaces = settings["NAMESPACES"]

def validade_url(s):
    if (type(s) != str ):
        return False

    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return (re.match(regex, s) is not None) 


def parse_ifs(value):
  if value is None:
      return ""
  try:
      n = int(value)
      return n
  except:
      try: 
        n = float (value)
        return n
      except:
        return value


def comboBox_by_itens(itens):
    comboBox = QComboBox()
    for item in itens:
        comboBox.addItem(item)
    return comboBox





class Layer2Triple:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Layer2Triple_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&QGISSPARQL')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        self.concepts = []
        self.fields_name = []
     


    def load_vocabulary(self, task, prefix, url, format):
            QgsMessageLog.logMessage('the task is already running.', 'Layer2Triple')
      
            g = Graph()
            g.parse(url, format=format)
            q = """
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX owl: <http://www.w3.org/2002/07/owl#>

                SELECT ?p
                WHERE 
                {
                    { ?p rdf:type owl:Class} UNION
                { ?p rdf:type owl:DatatypeProperty} UNION
                { ?p rdf:type owl:ObjectProperty} UNION
                { ?p rdf:type rdf:Property}    
                }
            """

            # Apply the query to the graph and iterate through results
            for r in g.query(q):
                attr = r["p"].split("#") 
                name = prefix+":"+attr[1]
                self.concepts.append(name)
            
            if prefix not in namespaces:
                namespaces[prefix] = (Namespace(url), format)

            QgsMessageLog.logMessage('Vocabulary loaded', 'Triple2Layer')
            
            return len(self.concepts)




    def filter_table(self):
        text = self.dlg.search_bar.text().lower()
        for row in range(self.dlg.tableAttributes.rowCount()):
            concept = self.dlg.tableAttributes.cellWidget(row, 0).text().lower()
            if text in concept:
                self.dlg.tableAttributes.setRowHidden(row, False)
            else:
                self.dlg.tableAttributes.setRowHidden(row, True)


    def fill_table(self,start):

            QgsMessageLog.logMessage('Loading table.', 'Layer2Triple')
            
            self.dlg.search_bar.setPlaceholderText("Filtrar concepts...")

            # Configura a tabela de atributos
            self.dlg.tableAttributes.setRowCount(len(self.concepts))
            self.dlg.tableAttributes.setColumnCount(3)
            self.dlg.tableAttributes.setHorizontalHeaderLabels(["Concepts", "Type", "Value"])

            for c in self.concepts[start:]:
                print(f"Debug: c = {c}, start = {start}")
                self.dlg.tableAttributes.setCellWidget(start, 0, QCheckBox(c))
                comboBox = QComboBox()
                comboBox.textActivated.connect(partial(self.combo_changed, start))
                comboBox.addItem("Constant Value")
                comboBox.addItem("Layer Attribute")
                comboBox.addItem("Vocabulary")
                self.dlg.tableAttributes.setCellWidget(start, 1, comboBox)
                self.dlg.tableAttributes.setCellWidget(start, 2, QLineEdit())
                start += 1

            self.dlg.search_bar.textChanged.connect(self.filter_table)

            for c in self.concepts:
                self.dlg.comboRDFType.addItem(c)
                self.dlg.comboRDFType_2.addItem(c)
                self.dlg.comboBoxPredicate.addItem(c)
                
            self.filter_table()


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Layer2Triple', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Layer2Triple/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Layer2Triple'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&QGISSPARQL'),
                action)
            self.iface.removeToolBarIcon(action)



    def show_group (self):
        if self.dlg.groupBoxConstants.isVisible():
            self.dlg.groupBoxConstants.setVisible(False)
        else:
            self.dlg.groupBoxConstants.setVisible(True)
        

    def comboID_clicked (self):
        if self.dlg.comboID.currentText() == "Layer Attribute":
            self.dlg.comboAttributeID.setEnabled(True)
        else:
            self.dlg.comboAttributeID.setEnabled(False)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = Layer2TripleMain()

            self.vocab_dlg = VocabularyDialog()

            #self.dlg.buttonLoad.clicked.connect(handle_dialog_vocabulary)

            self.vocab_dlg.buttonBox.accepted.connect(self.handle_dialog_vocabulary)
            self.dlg.buttonBox.accepted.connect(self.save_file)
            self.dlg.buttonBox.rejected.connect(self.close)
            self.dlg.button_load_layer.clicked.connect(self.load_fields)
            self.dlg.actionSave.triggered.connect(self.save_setting)
            self.dlg.actionOpen.triggered.connect(self.open_setting)
            self.dlg.actionLoad_Vocabulary.triggered.connect(self.show_dialog_vocabulary)

            self.dlg.pushShowGroup.clicked.connect(self.show_group)

            self.dlg.groupBoxConstants.setStyleSheet("QGroupBox { border: 0px; }")


            self.dlg.comboID.textActivated.connect(self.comboID_clicked)


                    #"http://purl.org/linked-data/sdmx/2009/dimension#""

        QgsMessageLog.logMessage('Task to loading vocabulary', 'Layer2Triple')                                        
        self.task = QgsTask.fromFunction('Loading vocabulary...', 
                                        self.load_vocabulary, 
                                        prefix="sdmx", url= "http://purl.org/linked-data/sdmx/2009/dimension#", format= "ttl", 
                                        on_finished=partial(self.fill_table_from_task)) 
    
        QgsApplication.taskManager().addTask(self.task)


        self.dlg.groupBoxConstants.setVisible(False)

        self.update_comboLayer()

    
        self.dlg.show()

    def show_dialog_vocabulary(self):
        self.vocab_dlg.show()



    def handle_dialog_vocabulary(self):
        format = self.vocab_dlg.comboFormat.currentText()
        url = self.vocab_dlg.lineURL.text()
        prefix = self.vocab_dlg.linePrefix.text()

        #"http://purl.org/linked-data/sdmx/2009/dimension#""

        QgsMessageLog.logMessage('Task to loading vocabulary', 'Layer2Triple')                                        
        self.task = QgsTask.fromFunction('Loading vocabulary...', 
                                        self.load_vocabulary, 
                                        prefix=prefix, url= url, format= format, 
                                        on_finished=partial(self.fill_table_from_task)) 
    
        QgsApplication.taskManager().addTask(self.task)
        
        #(self,task, prefix, namespace, format):

    def load_fields(self):
        
        try:
            self.layer = QgsProject.instance().mapLayersByName(self.dlg.comboLayer.currentText())[0]
            self.fields_name = []        

            fields = self.layer.fields()
            for field in fields:
                self.fields_name.append(field.name())

            self.fill_table(0)

            for attr in self.fields_name:
                self.dlg.comboAttributeID.addItem(attr)

            self.iface.messageBar().pushMessage(
                "Success", "Load Layer fields",
                level=Qgis.Success, duration=3
            )
        except:
            
            self.iface.messageBar().pushMessage(
            "Error", "No layer loading",
            level=Qgis.Info, duration=3)


    def update_comboLayer(self):
        self.dlg.comboLayer.clear()

        for layer in QgsProject.instance().mapLayers().values():
            if type(layer) == QgsVectorLayer:
                self.dlg.comboLayer.addItem(layer.name())
                

    def combo_changed(self,row, s):
        if (s == "Layer Attribute"):
            self.dlg.tableAttributes.setCellWidget(row, 2, comboBox_by_itens(self.fields_name))
        elif (s == "Vocabulary"):
            self.dlg.tableAttributes.setCellWidget(row, 2, comboBox_by_itens (self.concepts))
        else:
            self.dlg.tableAttributes.setCellWidget(row, 2, QLineEdit())


    def toURL (self, str):
        rdf_attr = str
        rdf = rdf_attr.split(":")
        rdf_attr = rdf[1]
        namespace = namespaces[rdf[0]][0]
        return namespace[rdf_attr]


    def save_setting(self):
        pass
            
                
    def open_setting(self):
        pass


    def fill_table_from_task(self, exception, quant_concepts=None):
        print  ("fill_table", exception)
        if not exception:
            self.fill_table(0)       
            self.iface.messageBar().pushMessage(
                "Success",
                f"Configuration uploaded successfully...{quant_concepts} concepts loaded,{exception} mistakes",
                level=Qgis.Success,
                duration=3
            )
        else:
           self.iface.messageBar().pushMessage(
                "Erro on load Vocabulario",
                f"{exception}",
                level=Qgis.Warning,
                duration=3
            )
        
    # dicts atributos e vocabulários selecionados
    def read_selected_attributes(self):
        mVocab = {}
        saveAttrs = {}
        save_constants = {}

        for row in range(self.dlg.tableAttributes.rowCount()): 
            check = self.dlg.tableAttributes.cellWidget(row, 0) 
            if check.isChecked():
                rdf_attr = check.text()
                rdf = rdf_attr.split(":")
                rdf_attr = rdf[1]
                namespace = namespaces[rdf[0]][0]
                url_rdf = namespace[rdf_attr]

                combo_type = self.dlg.tableAttributes.cellWidget(row, 1)

                if combo_type.currentText() == "Layer Attribute":
                    combo = self.dlg.tableAttributes.cellWidget(row, 2)
                    attribute = combo.currentText()
                    saveAttrs[attribute] = rdf_attr
                    mVocab[attribute] =  url_rdf
                elif combo_type.currentText() == "Vocabulary":
                    combo = self.dlg.tableAttributes.cellWidget(row, 2)
                    attribute = combo.currentText()
                    url_v = self.toURL(attribute)
                    save_constants[rdf_attr] = url_v
                    mVocab[rdf_attr] =  url_rdf
                else:
                    line_edit = self.dlg.tableAttributes.cellWidget(row, 2)
                    save_constants[rdf_attr] = parse_ifs(line_edit.text())
                    mVocab[rdf_attr] =  url_rdf

        return mVocab, saveAttrs, save_constants
        

    # features da Camada
    def get_layer_features(self):
        if self.dlg.checkSelected.isChecked():
            features = self.layer.selectedFeatures() 
        else:
            features = self.layer.getFeatures()

        return features

    # criação das triplas RDF
    def create_rdf_triples(self, features, saveAttrs,mVocab):
        triples = {}
        for feature in features:
            triple = {}
            mVocab['asWkt'] = URIRef("http://www.opengis.net/ont/geosparql#asWKT")
            if self.dlg.checkGeometries.isChecked():
                pol = QgsMultiPolygon()
                pol.fromWkt(feature.geometry().asWkt())
                triple['asWkt'] = pol.polygonN(0).asWkt()

            for key in saveAttrs:
                triple[key] = feature[key]

            if self.dlg.comboID.currentText() == "Layer Attribute":
                attr = feature[self.dlg.comboAttributeID.currentText()]
                triples[attr] = triple
            else:
                triples[str(uuid.uuid4())] = triple

        print (triples)
        print (len(triples))
        return triples

    # criação do Grafo RDF
    def create_rdf_graph(self,mainNamespace, prefixes, save_constants,mVocab,triples):
        
        g = Graph()
        
        g.bind(self.dlg.linePrefix2.text(), mainNamespace)
        g.bind("geo", Namespace("http://www.opengis.net/ont/geosparql#"))

        constants_p_o = []
        for key in save_constants:
            attr = key
            value = save_constants[key]
            predicate = mVocab[attr]
            if isinstance(value, URIRef):
                object = value
            else:
                object = Literal(value)
                if validade_url(value): # talvez deveria ver pelo schema
                    object = URIRef(value)
            constants_p_o.append((predicate, object))

        if self.dlg.checkConstant.isChecked(): # aggregar em um dataset, por exemplo
            aggregNamespace = Namespace(self.dlg.lineURLBase_2.text())
            g.bind(self.dlg.linePrefix2_2.text(), aggregNamespace)

            aggregate = aggregNamespace[str(uuid.uuid4())] 
            attribute = self.dlg.comboRDFType_2.currentText()
            url_aggregate = self.toURL(attribute)

            g.add((aggregate, RDF.type, url_aggregate))

            for (p, o) in constants_p_o:
                g.add((aggregate, p, o))

        for prefix, name in prefixes.items():
            g.bind(prefix, name[0])

        
        for id, attributes in triples.items():
            print ("id", id)
            subject = mainNamespace[id]
            attribute = self.dlg.comboRDFType.currentText()
            url_v = self.toURL(attribute)
            g.add((subject, RDF.type, url_v))
            print ("attributes", attributes)
            for attr, value in attributes.items():
                predicate = mVocab[attr]
                object = Literal(value)
                if (validade_url(value)):# talvez deveria ver pelo schema
                    object = URIRef(value)

                g.add((subject, predicate, object))
                print (subject, predicate, object)


            if self.dlg.checkConstant.isChecked(): # agregar em um dataset, por exemplo
                attribute_p = self.dlg.comboBoxPredicate.currentText()
                url_p = self.toURL(attribute_p)
                g.add((subject, url_p, aggregate))
            else:
                for (p, o) in constants_p_o:
                    g.add((subject, p, o))

        return g
        
    # metodo principal para save_file
    def save_file(self):
        try:                                                                                       
            path = str(QFileDialog.getSaveFileName(caption="Defining output file", filter="Terse RDF Triple Language(*.ttl);;XML Files (*.xml)")[0])

            #Secionei essas partes pegando somente o retorno de cada função e encapsulando
            mVocab, saveAttrs, save_constants = self.read_selected_attributes()
            features = self.get_layer_features()  
   
            #aqui ele faz feature por feature, entao o processamento de dados é grande 
            #print(f'triples:{triples}')
            g=Graph()
            
            url_main = self.dlg.lineURLBase.text()
            mainNamespace = Namespace(url_main)
            
            #avaliar isso aqui para saber se tem mesma funcionalidade
            prefixes = namespaces.copy()
            prefixes["geo"] = Namespace("http://www.opengis.net/ont/geosparql#")


            #com task
        #    QgsMessageLog.logMessage('criando tarefa.', 'Layer2Triple')                                                    
         #   self.task2 = QgsTask.fromFunction('Loading settings...', self.create_rdf_triples,features, saveAttrs,mVocab,on_finished=partial(self.create_rdf_graph,path,mainNamespace, prefixes, save_constants,mVocab)) 
          #  QgsApplication.taskManager().addTask(self.task2)
            
            #sem task
            triples = self.create_rdf_triples(features, saveAttrs,mVocab)#processo intenso na cpu 
            g = self.create_rdf_graph(mainNamespace, prefixes, save_constants,mVocab,triples) #processo intenso na cpu
            s = g.serialize(format="turtle")

            f = open(path, "w+", encoding="utf-8")
            print ("saving ..."+path)
            f.write(s)
            f.close()
        
            print("tarefa concluida")
            self.iface.messageBar().pushMessage(
                "Success", "Output file written at " + path,
                level=Qgis.Success, duration=3
            )
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Error",
                f"error {e} to save file",
                level=Qgis.Warning,
                duration=3
            )
            print(f"error {e} to save file",)
        
        
    def close(self):
        self.dlg.setVisible(False)