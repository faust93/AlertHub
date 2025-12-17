<template>
<div style="padding: 10px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="margin: 0;">Alert Templates</h3>
        <el-button type="primary"
        @click="dialogAddTemplate = true">Add</el-button>
    </div>
    <el-collapse accordion @change="onCollapseChange">
      <template v-for="(item, index) in templatesData" :key="index">
        <el-collapse-item :title="item.name" :name="item.name">
            <template #title>
                <el-button type="danger" :icon="Delete" style="margin-right: 10px;" @click.stop="ontemplateDelete(item.id)"></el-button>
                <span style="font-size: 15px;"><el-tag type="info" effect="plain">{{ item.id }}</el-tag> {{ item.name }} - {{ item.description }}</span>
            </template>
            <div>
                <el-row>
                <el-col :span="4">
                <div style="display: flex; flex-direction: column;">
                 <label style="font-size: 12px; margin-bottom: 4px;">Name</label>
                 <el-input
                    v-model="templateName"
                    style="width: 90%"
                    placeholder="Template name here"
                    clearable
                    />
                </div>
                </el-col>
                <el-col :span="8">
                <div style="display: flex; flex-direction: column;">
                 <label style="font-size: 12px; margin-bottom: 4px;">Description</label>
                 <el-input
                    type="textarea"
                    :rows="1"
                    v-model="templateDescription"
                    style="width: 100%"
                    placeholder="Template description here"
                    clearable
                    />
                </div>
                </el-col>
                </el-row>
                <el-divider content-position="left">JSON Alert Data</el-divider>
                <el-input
                    type="textarea"
                    :rows="3"
                    v-model="alertJSON"
                    style="width: 100%"
                    placeholder="Alert JSON data"
                    clearable
                    />
                <el-divider content-position="left">Template</el-divider>
                <div style="height: 500px">
                <el-splitter>
                <el-splitter-panel size="50%">
                  <PrismEditor class="my-editor-tpl"
                    v-model="templateCode"
                    :highlight="highlighter_tpl"
                    :tabSize="4"
                    line-numbers
                  />
                </el-splitter-panel>
                <el-splitter-panel size="30%">
                  <PrismEditor class="my-editor-tpl"
                    v-model="templateRender"
                    :highlight="highlighter_tpl"
                    :readonly="true"
                  />
                </el-splitter-panel>
                </el-splitter>
                </div>
                <div style="display: flex;  margin-top: 16px;">
                    <el-button class="transfer-footer" @click="onTemplateUpdate(item.id)" type="primary">Save</el-button>
                    <el-button class="transfer-footer" @click="onTemplatePreview()" type="success">Preview</el-button>
                </div>
            </div>
        </el-collapse-item>
      </template>
    </el-collapse>
</div>

<el-dialog
    v-model="dialogAddTemplate"
    title="Add Template"
    width="500"
    :modal="false">
    <el-form
      ref="TemplateFormRef"
      :model="TemplateForm"
      :rules="TemplateFormRules"
      label-position="left">
      <el-form-item label="Name" prop="name" label-width="100px">
        <el-input v-model="TemplateForm.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Description" prop="description" label-width="100px">
        <el-input v-model="TemplateForm.description" autocomplete="off" :rows="2" type="textarea" placeholder="Please describe the template"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddTemplate = false">Cancel</el-button>
        <el-button type="primary" @click="onAddTemplateForm(TemplateFormRef)">Add</el-button>
      </div>
    </template>
</el-dialog>

</template>

<script setup>
import { ref, reactive, computed, onMounted  } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { highlight, languages } from 'prismjs'
import 'prismjs/components/prism-python'
import 'prismjs/themes/prism-dark.css'
import { PrismEditor } from 'vue-prism-editor';
import 'vue-prism-editor/dist/prismeditor.min.css'; // import the styles
import { GetTemplates, AddTemplate, DeleteTemplate, UpdateTemplate, RenderTemplate } from '@/request/api.js'

const dialogAddTemplate = ref(false)

const templatesData = ref([])
const templateName = ref('')
const templateDescription = ref('')
const templateCode = ref('')
const templateRender = ref('')

const alertJSON = ref('{"alert_id":"ed673888f299c2f1","alertname":"JvmHeapMemoryWarning","severity":"warning","instance":"dev-host.company.com","job":"-","status":"resolved","annotations":{"description":"Jvm heap memory is over threshold for service-1 app on dev-host.company.com (current value: 92.18885902882967%)","link":"https://wiki.company.com/monitoring/AlertPlabook","summary":"JVM Memory in heap area is over threshold"},"labels":{"alertgroup":"jvm.rules","alertname":"JvmHeapMemoryWarning","application":"service-1","environment":"dev","instance":"dev-host.company.com","severity":"warning"},"generatorURL":"http://monitoring.company.com:8880/vmalert/alert?group_id=12635588474808178526&alert_id=2529406891918503755","updatedAt":"2025-08-25T17:52:41","endsAt":"2025-08-25T17:36:00","startsAt":"2025-08-25T17:35:00Z"}')

const TemplateFormRef = ref()
const TemplateForm = reactive({
  name: '',
  description: '',
  template: ''
})
const TemplateFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  description: [{ required: true, message: 'Description is required', trigger: 'blur' }],
})

const highlighter_tpl = (codeStr) => {
  return highlight(codeStr, languages.python)
}

function onCollapseChange(activeName) {
    if(!activeName) return
    let tpl = templatesData.value.filter(item => item.name === activeName)[0]
    templateName.value = tpl.name
    templateDescription.value = tpl.description
    templateCode.value = tpl.template
    templateRender.value = ''
}

async function onTemplateDelete(pid) {
  let res = await DeleteTemplate(pid);
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Removed successfully')
    //fetchTemplates()
  } else {
    ElMessage.error('Error removing item')
  }
}

function onAddTemplateForm(formEl) {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddTemplate({
            name: TemplateForm.name,
            description: TemplateForm.description,
            template: TemplateForm.template
        });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddTemplate.value = false;
            fetchTemplates()
      } else {
            ElMessage.error('Error adding team');
      }
    } else {
        ElMessage.error('Error adding team');
    }
  })
}

async function onTemplateUpdate(pid) {
  let res = await UpdateTemplate({
      id: pid,
      name: templateName.value,
      description: templateDescription.value,
      template: templateCode.value
    });
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Updated successfully')
    fetchTemplates()
  } else {
    ElMessage.error('Error updating team')
  }
}

async function onTemplatePreview() {
  let res = await RenderTemplate({
      alert_json: alertJSON.value,
      template: templateCode.value
    });
    if ('msg' in res && res.msg === "ok") {
      templateRender.value = res.result
    }
}

async function fetchTemplates() {
  let res = await GetTemplates()
  templatesData.value = res
}

onMounted(async () => {
  fetchTemplates()
})
</script>

<style>
  /* required class */
  .my-editor-tpl {
    /* we dont use `language-` classes anymore so thats why we need to add background and text color manually */
    background: #2d2d2d;
    color: #ccc;

    /* you must provide font-family font-size line-height. Example: */
    font-family: Fira code, Fira Mono, Consolas, Menlo, Courier, monospace;
    font-size: 16px;
    line-height: 1.5;
    padding: 5px;
  }

  /* optional class for removing the outline */
  .prism-editor__textarea:focus {
    outline: none;
  }
</style>
