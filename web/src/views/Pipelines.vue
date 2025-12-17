<template>
<div style="padding: 10px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="margin: 0;">Alert Pipelines</h3>
        <el-button type="primary"
        @click="dialogAddPipeline = true">Add</el-button>
    </div>
    <el-collapse accordion @change="onCollapseChange">
      <template v-for="(item, index) in pipelinesData" :key="index">
        <el-collapse-item :title="item.name" :name="item.name">
            <template #title>
                <el-button type="danger" :icon="Delete" style="margin-right: 10px;" @click.stop="onPipelineDelete(item.id)"></el-button>
                <span style="font-size: 15px;">{{ item.name }} - {{ item.description }}</span>
            </template>
            <div>
                <el-row>
                <el-col :span="4">
                <div style="display: flex; flex-direction: column;">
                 <label style="font-size: 12px; margin-bottom: 4px;">Name</label>
                 <el-input
                    v-model="pipelineName"
                    style="width: 90%"
                    placeholder="Pipeline name here"
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
                    v-model="pipelineDescription"
                    style="width: 100%"
                    placeholder="Pipeline description here"
                    clearable
                    />
                </div>
                </el-col>
                </el-row>
                <el-divider content-position="left">Pipeline code</el-divider>
                <PrismEditor class="my-editor"
                   v-model="pipelineCode"
                   :highlight="highlighter"
                   :tabSize="4"
                   line-numbers
                />
                <div style="display: flex;  margin-top: 16px;">
                    <el-button class="transfer-footer" @click="onPipelineUpdate(item.id)" type="primary">Save</el-button>
                    <el-button class="transfer-footer" @click="onPipelineValidate(item.id)" type="success">Validate</el-button>
                </div>
            </div>
        </el-collapse-item>
      </template>
    </el-collapse>
</div>

<el-dialog
    v-model="dialogAddPipeline"
    title="Add Pipeline"
    width="500"
    :modal="false">
    <el-form
      ref="PipelineFormRef"
      :model="PipelineForm"
      :rules="PipelineFormRules"
      label-position="left">
      <el-form-item label="Name" prop="name" label-width="100px">
        <el-input v-model="PipelineForm.name" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Description" prop="description" label-width="100px">
        <el-input v-model="PipelineForm.description" autocomplete="off" :rows="2" type="textarea" placeholder="Please describe the pipeline"/>
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddPipeline = false">Cancel</el-button>
        <el-button type="primary" @click="onAddPipelineForm(PipelineFormRef)">Add</el-button>
      </div>
    </template>
</el-dialog>

</template>

<script setup>
import { ref, reactive, computed, onMounted  } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import { highlight, languages } from 'prismjs'
import 'prismjs/components/prism-yaml'
import 'prismjs/themes/prism-dark.css'
import { PrismEditor } from 'vue-prism-editor';
import 'vue-prism-editor/dist/prismeditor.min.css'; // import the styles
import { GetPipelines, AddPipeline, UpdatePipeline, DeletePipeline, ValidatePipeline } from '@/request/api.js'

const dialogAddPipeline = ref(false)

const pipelinesData = ref([])
const pipelineName = ref('')
const pipelineDescription = ref('')
const pipelineCode = ref('---')

const PipelineFormRef = ref()
const PipelineForm = reactive({
  name: '',
  description: '',
  yaml_content: ''
})
const PipelineFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  description: [{ required: true, message: 'Description is required', trigger: 'blur' }],
})

const highlighter = (codeStr) => {
  return highlight(codeStr, languages.yaml)
}

function onCollapseChange(activeName) {
    if(!activeName) return
    let pipe = pipelinesData.value.filter(item => item.name === activeName)[0]
    pipelineName.value = pipe.name
    pipelineDescription.value = pipe.description
    pipelineCode.value = pipe.yaml_content
}

async function onPipelineDelete(pid) {
  let res = await DeletePipeline(pid);
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Removed successfully')
    //fetchPipelines()
  } else {
    ElMessage.error('Error removing item')
  }
}

function onAddPipelineForm(formEl) {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddPipeline({
            name: PipelineForm.name,
            description: PipelineForm.description,
            yaml_content: PipelineForm.yaml_content
        });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddPipeline.value = false;
            fetchPipelines()
      } else {
            ElMessage.error('Error adding team');
      }
    } else {
        ElMessage.error('Error adding team');
    }
  })
}

async function onPipelineUpdate(pid) {
  let res = await UpdatePipeline({
      id: pid,
      name: pipelineName.value,
      description: pipelineDescription.value,
      yaml_content: pipelineCode.value
    });
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Updated successfully')
    fetchPipelines()
  } else {
    ElMessage.error('Error updating team')
  }
}

async function onPipelineValidate() {
  let res = await ValidatePipeline({
      pipeline: pipelineCode.value
    });
  if ('msg' in res && res.msg === "ok") {
    const v_state = res.result === "OK" ? "success" : "error"
    ElNotification({
      title: 'Validation ' + v_state,
      type: v_state,
      message: res.result,
      duration: 0
    })
  } else {
    ElMessage.error('Unable to validate pipeline')
  }
}

async function fetchPipelines() {
  let res = await GetPipelines()
  pipelinesData.value = res
}

onMounted(async () => {
  fetchPipelines()
})
</script>

<style>
  /* required class */
  .my-editor {
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
