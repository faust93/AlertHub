<template>
  <div style="padding: 10px;">
    <el-tabs v-model="activeTab" class="demo-tabs" @tab-click="">
      <el-tab-pane label="Users" name="users">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
          <h3 style="margin: 0;">Users</h3>
          <el-button v-if="userRole === '0'" type="primary" @click="onAddUser()">Add</el-button>
        </div>
        <el-table v-loading="loading" :data="tbUserData"
          style="width: 100%; height: calc(100vh - 240px); overflow: auto;">

          <el-table-column label="Id" prop="id" width="50">
            <template #default="scope">
              {{ scope.row.id }}
            </template>
          </el-table-column>

          <el-table-column label="Name" prop="name">
            <template #default="scope">
              {{ scope.row.name }}
            </template>
          </el-table-column>

          <el-table-column label="Email" prop="email">
            <template #default="scope">
              {{ scope.row.email }}
            </template>
          </el-table-column>

          <el-table-column label="Teams" prop="role">
            <template #default="scope">
              <el-tag v-for="(t, idx) in getUserTeams(scope.row.id)" :key="idx" style="margin-right: 4px">
                {{ t }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="Role" prop="role">
            <template #default="scope">
              {{ getRoleName(scope.row.role) }}
            </template>
          </el-table-column>

          <el-table-column label="Operations" width="150">
            <template #default="scope">
              <el-button :disabled="userRole != '0' && userId != scope.row.name" type="primary" size="small"
                :icon="Edit" @click="onEditUser(scope.row)">
              </el-button>
              <el-button :disabled="userRole != '0'" type="danger" size="small" :icon="Delete"
                @click="() => { userToDelete = scope.row.name; userToDeleteId = scope.row.id; dialogDeleteUser = true }">
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Teams tab -->
      <el-tab-pane label="Teams" name="teams">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
          <h3 style="margin: 0;">Teams</h3>
          <el-button v-if="userRole === '0'" type="primary" @click="dialogAddTeam = true">Add</el-button>
        </div>
        <el-collapse accordion @change="funcCollapseChange">
          <template v-for="(item, index) in teamsData" :key="item">
            <el-collapse-item :title="item.name" :name="item.name">
              <template #title>
                <el-button v-if="userRole === '0'" type="danger" :icon="Delete" style="margin-right: 10px;"
                  @click.stop="onTeamDelete(item.id)"></el-button>
                <span style="font-size: 15px;">{{ item.name }}</span>
              </template>
              <div>
                <el-transfer v-model="selectedUsers" style="text-align: left; display: inline-block"
                  :titles="['All users', 'Team members']" :data="allUsers" filterable filter-placeholder="Search here">
                  <template #default="{ option }">
                    <span>{{ option.label }}</span>
                  </template>
                </el-transfer>
                <div style="display: flex;  margin-top: 16px;">
                  <el-button class="transfer-footer" @click="onTeamUpdate(item.id, item.name)" type="primary">Save</el-button>
                </div>
              </div>
            </el-collapse-item>
          </template>
        </el-collapse>
      </el-tab-pane>
    </el-tabs>
  </div>

  <el-dialog v-model="dialogAddUser" :title="userFormTitle" width="500" :modal="false">
    <el-form ref="addUserFormRef" label-width="auto" :model="addUserForm" :rules="addUserFormRules" >
      <el-form-item label="Name" prop="name" >
        <el-input v-model="addUserForm.name" :disabled="isNameDisabled" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Password" prop="password" >
        <el-input v-model="addUserForm.password" type="password" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Email" prop="email" >
        <el-input v-model="addUserForm.email" autocomplete="off" />
      </el-form-item>
      <el-form-item label="Admin" prop="admin" >
        <el-checkbox v-model="addUserForm.role" label="Admin privileges" />
      </el-form-item>
      <el-form-item label="Timezone" prop="timezone" >
        <el-input v-model="addUserForm.timezone" autocomplete="off" />
      </el-form-item>
      <el-alert type="info" show-icon :closable="false">
        <p>Notification Channels</p>
      </el-alert><br />
      <el-form-item label="Telegram ID" prop="telegram_id" >
        <el-input v-model="addUserForm.telegram_id" autocomplete="off" placeholder="User's Chat ID" />
      </el-form-item>
      <el-form-item label="Ntfy Topic" prop="ntfy" >
        <el-input v-model="addUserForm.ntfy" autocomplete="off" placeholder="Notification topic name"/>
      </el-form-item>
      <el-form-item label="Apprise URI" prop="apprise" >
        <el-input v-model="addUserForm.apprise" autocomplete="off" placeholder="Notifier URI string"/>
      </el-form-item>
      <el-form-item label="Active Channels" prop="notifiers" >
        <el-cascader v-model="selectedNotifiers" placeholder="Specify notification channel" :options="notifiers"
          :props="{ multiple: true, }" filterable style="width: 100%;" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogAddUser = false">Cancel</el-button>
        <el-button type="primary" @click="submitAddUserForm(addUserFormRef)">Save</el-button>
      </div>
    </template>
  </el-dialog>

  <el-dialog v-model="dialogDeleteUser" title="Confirm Delete" width="400" :modal="false">
    <span>Are you sure you want to delete user <b>{{ userToDelete }}</b>?</span>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogDeleteUser = false">Cancel</el-button>
        <el-button type="danger" @click="confirmDeleteUser">Delete</el-button>
      </div>
    </template>
  </el-dialog>

  <el-dialog v-model="dialogAddTeam" title="Add Team" width="500" :modal="false">
    <el-form ref="addTeamFormRef" label-width="auto" :model="addTeamForm" :rules="addTeamFormRules">
      <el-form-item label="Team name" prop="name" >
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
import { reactive, ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Delete, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { GetUsers, GetTeams, AddTeam, AddUser, DeleteUser, DeleteTeam, UpdateUser, UpdateTeam } from '@/request/api.js'
import { isValidTimeZone } from '@/utils/utils'

const route = useRoute()

const userRole = localStorage.getItem('user_role') || ''
const userId = localStorage.getItem('user_id') || ''

const query_user_id = route.params.user_id || null

// teams vars
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

const activeTab = ref('users')
const loading = ref(false)
const tbUserData = ref([])

const getRoleName = (role) => {
  switch (role) {
    case 0:
      return 'Admin'
    case 1:
      return 'User'
  }
}

const notifiers = [
  //{ value: 1, label: "Email"},
  { value: 2, label: "Telegram"},
  { value: 3, label: "Ntfy"},
  { value: 4, label: "Apprise"}
]
const selectedNotifiers = ref([])

let submitAddUserForm
let userToDelete, userToDeleteId
let isNameDisabled = false
let userFormTitle = ''

const dialogAddUser = ref(false)
const dialogDeleteUser = ref(false)
const addUserFormRef = ref()
const addUserForm = reactive({
  name: '',
  password: '',
  email: '',
  notifiers: '',
  telegram_id: '',
  ntfy: '',
  apprise: '',
  timezone: '',
  role: 0
})

const addUserFormRules = reactive({
  name: [{ required: true, message: 'Name is required', trigger: 'blur' }],
  password: [{ required: true, message: 'Password is required', trigger: 'blur' }],
  email: [{ required: true, message: 'Email is required', trigger: 'blur' }],
  timezone: [{ validator: checkTimezone, trigger: 'change' }],
})

function checkTimezone(rule, value, callback) {
    if (value && !isValidTimeZone(value) && value !== 'Local') {
        return callback(new Error('Invalid timezone format'))
    } else {
        callback()
    }
}

function funcAddUserForm(formEl) {
    if (!formEl) return;
    if(selectedNotifiers.value) {
        let ids = selectedNotifiers.value.map(item => item[0])
        addUserForm.notifiers = JSON.stringify(ids)
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await AddUser({
            name: addUserForm.name,
            password: addUserForm.password,
            email: addUserForm.email,
            notifiers: addUserForm.notifiers,
            telegram_id: addUserForm.telegram_id,
            ntfy: addUserForm.ntfy,
            apprise: addUserForm.apprise,
            timezone: addUserForm.timezone,
            role: addUserForm.role == true ? 0 : 1
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Added successfully');
            dialogAddUser.value = false;
            fetchUsers()
            fetchTeamUsers()
      } else {
            ElMessage.error('Error adding new user');
      }
    } else {
        ElMessage.error('Error adding new user');
    }
  })
}

function funcUpdateUserForm(formEl) {
    if (!formEl) return;
    if(selectedNotifiers.value) {
        let ids = selectedNotifiers.value.map(item => item[0])
        addUserForm.notifiers = JSON.stringify(ids)
    }
    formEl.validate(async (valid) => {
    if (valid) {
      console.log('Form is valid, submitting...')
      let res = await UpdateUser({
            name: addUserForm.name,
            password: addUserForm.password,
            email: addUserForm.email,
            notifiers: addUserForm.notifiers,
            telegram_id: addUserForm.telegram_id,
            ntfy: addUserForm.ntfy,
            apprise: addUserForm.apprise,
            timezone: addUserForm.timezone,
            role: addUserForm.role == true ? 0 : 1,
            password_update: addUserForm.password == 'DoNotChange' ? 0 : 1
      });
      if ('msg' in res && res.msg === "ok") {
            ElMessage.success('Updated successfully');
            dialogAddUser.value = false;
            fetchUsers()
            fetchTeamUsers()
            if (userId === addUserForm.name) {
              localStorage.setItem('user_tz', addUserForm.timezone)
            }
      } else {
            ElMessage.error('Error updating user');
      }
    } else {
        ElMessage.error('Error updating user');
    }
  })
}

function onEditUser(row) {
  userFormTitle = "Edit user"
  isNameDisabled = true
  selectedNotifiers.value = row.notifiers.map(item => [item])
  addUserForm.name = row.name
  addUserForm.password = 'DoNotChange'
  addUserForm.email = row.email
  addUserForm.notifiers = selectedNotifiers.value
  addUserForm.telegram_id = row.telegram_id
  addUserForm.ntfy = row.ntfy
  addUserForm.apprise = row.apprise
  addUserForm.timezone = isValidTimeZone(row.timezone) ? row.timezone : 'Local'
  addUserForm.role = row.role == 0 ? true : false
  dialogAddUser.value = true
  submitAddUserForm = funcUpdateUserForm
}

function onAddUser() {
  userFormTitle = "Add new user"
  submitAddUserForm = funcAddUserForm
  selectedNotifiers.value = []
  isNameDisabled = false
  addUserForm.name = ''
  addUserForm.password = ''
  addUserForm.email = ''
  addUserForm.notifiers = ''
  addUserForm.telegram_id = ''
  addUserForm.ntfy = ''
  addUserForm.apprise = ''
  addUserForm.timezone = 'Local'
  addUserForm.role = false
  dialogAddUser.value = true
}

const confirmDeleteUser = async () => {
  let params = {name: userToDelete, id: userToDeleteId}
  let res = await DeleteUser(params)
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Deleted successfully');
    dialogDeleteUser.value = false;
    fetchUsers()
    fetchTeamUsers()
  } else {
     ElMessage.error('Error deleting a user');
  }
}

async function fetchUsers() {
  let res = await GetUsers()
  tbUserData.value = res
}

// teams
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
            fetchTeamUsers()
            fetchTeams()
      } else {
            ElMessage.error('Error adding team');
      }
    } else {
        ElMessage.error('Error adding team');
    }
  })
}

async function onTeamUpdate(tid, name) {
  let res = await UpdateTeam({
      id: tid,
      name: name,
      members: JSON.stringify(selectedUsers.value)
    });
  if ('msg' in res && res.msg === "ok") {
    ElMessage.success('Updated successfully')
    fetchTeamUsers()
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

async function fetchTeamUsers() {
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
  await fetchUsers()
  fetchTeamUsers()
  fetchTeams()

  if (query_user_id) {
    try {
      const user = tbUserData.value.find(item => item.name === query_user_id)
      if (!user) {
        console.warn(`No user found with ID: ${query_user_id}`)
        return
      }
      onEditUser(user)
    } catch (error) {
      console.error(`Failed to open user ID settings: ${query_user_id}`, error)
    }
}
})

const getUserTeams = (uId) => {
  const teamNames = teamsData.value
  .filter(team => team.members.includes(uId))
  .map(team => team.name) //.join(", ")
  return teamNames
}

</script>

<style>
.transfer-footer {
  padding: 6px 5px 5px 5px;
  display: flex;
  align-items: center;
}

.el-scrollbar__bar.is-horizontal {
  display: none;
}
</style>