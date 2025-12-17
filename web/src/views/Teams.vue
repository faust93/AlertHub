<template>
<div style="padding: 10px;">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="margin: 0;">Teams</h3>
        <el-button v-if="userRole === '0'" type="primary"
        @click="dialogAddTeam = true">Add</el-button>
    </div>
    <el-collapse accordion @change="funcCollapseChange">
      <template v-for="(item, index) in teamsData" :key="item">
        <el-collapse-item :title="item.name" :name="item.name">
            <template #title>
                <el-button v-if="userRole === '0'" type="danger" :icon="Delete" style="margin-right: 10px;" @click.stop="onTeamDelete(item.id)"></el-button>
                <span style="font-size: 15px;">{{ item.name }}</span>
            </template>
            <div>
                <el-transfer
                    v-model="selectedUsers"
                    style="text-align: left; display: inline-block"
                    :titles="['All users', 'Team members']"
                    :data="allUsers"
                    filterable
                    filter-placeholder="Search here"
                    >
                    <template #default="{ option }">
                        <span>{{ option.label }}</span>
                    </template>
                </el-transfer>
                <div style="display: flex;  margin-top: 16px;">
                    <el-button class="transfer-footer" @click="onTeamUpdate(item.name)" type="primary">Save</el-button>
                </div>
            </div>
        </el-collapse-item>
      </template>
    </el-collapse>
</div>

<el-dialog
    v-model="dialogAddTeam"
    title="Add Team"
    width="500"
    :modal="false">
    <el-form
      ref="addTeamFormRef"
      :model="addTeamForm"
      :rules="addTeamFormRules">
      <el-form-item label="Team name" prop="name" label-width="150px">
        <el-input v-model="addTeamForm.name" autocomplete="off" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddTeam = false">Cancel</el-button>
        <el-button type="primary" @click="funcAddTeamForm(addTeamFormRef)">Add</el-button>
      </div>
    </template>
</el-dialog>

</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetUsers, GetTeams, AddTeam, UpdateTeam, DeleteTeam } from '@/request/api.js'

const userRole = ref(localStorage.getItem('user_role') || '')

const loading = ref(false)
const dialogAddTeam = ref(false)

const userData = ref([])
const teamsData = ref([])

const selectedUsers = ref([])
const allUsers = ref([])

const addTeamFormRef = ref()
const addTeamForm = reactive({
  name: '',
  members: ''
})

const addTeamFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
})

function funcAddTeamForm(formEl) {
    if (!formEl) return;
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddTeam({
            name: addTeamForm.name,
            members: addTeamForm.members
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddTeam.value = false;
            fetchUsers()
            fetchTeams()
      } else {
            ElMessage.error('Error adding team');
      }
    } else {
        ElMessage.error('Error adding team');
    }
  })
}

async function onTeamUpdate(name) {
  let res = await UpdateTeam({
      name: name,
      members: JSON.stringify(selectedUsers.value)
    });
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Updated successfully')
    fetchUsers()
    fetchTeams()
  } else {
    ElMessage.error('Error updating team')
  }
}

async function onTeamDelete(team) {
  let res = await DeleteTeam(team);
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Removed successfully')
    fetchTeams()
  } else {
    ElMessage.error('Error removing team')
  }
}

async function fetchUsers() {
  loading.value = true
  let res = await GetUsers()
  userData.value = res
  loading.value = false

  allUsers.value = userData.value.map((user, idx) => ({
    key: user.id,
    label: user.name,
    disabled: false
  }))
}

async function fetchTeams() {
  loading.value = true
  let res = await GetTeams()
  teamsData.value = res
  loading.value = false
}

function funcCollapseChange(activeName) {
  if(!activeName) return;
  selectedUsers.value = []
  let members = teamsData.value.filter(item => item.name === activeName)
  if (members.length > 0 && members[0].members.length > 0) {
    let memberIds = members[0].members
    selectedUsers.value = userData.value.filter(item => memberIds.includes(item.id)).map(item => item.id)
  }
}

const transferredItems = computed(() => {
  return allUsers.value.filter(item =>
    selectedUsers.value.includes(item.key)
  )
})

onMounted(async () => {
  fetchUsers()
  fetchTeams()
})

</script>

<style>
.transfer-footer {
  padding: 6px 5px 5px 5px;
  display: flex;
  align-items: center;
}
</style>