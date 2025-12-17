<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginAPI } from "@/request/api.js"

const router = useRouter()

const ruleFormRef = ref();
const ruleForm = reactive({
    userName: '',
    password: ''
});

const checkUserName = (rule, value, callback) => {
    if (value === '') {
        return callback(new Error('Please enter your username'));
    } else {
        callback();
    }
};

const checkPassword = (rule, value, callback) => {
    if (value === '') {
        callback(new Error('Please enter your password'));
    } else {
        callback();
    }
};

const rules = reactive({
    userName: [{ validator: checkUserName, trigger: 'blur' }],
    password: [{ validator: checkPassword, trigger: 'blur' }],
});

const submitForm = (formEl) => {
    if (!formEl) return;

    formEl.validate(async (valid) => {
        if (valid) {
            console.log('Form validation OK');

            let res = await loginAPI({
                username: ruleForm.userName,
                password: ruleForm.password
            });
            if ('token' in res) {
                    ElMessage.success('Login successfully');
                    localStorage.setItem('token',  res.token)
                    localStorage.setItem('user_id', res.user_id)
                    localStorage.setItem('user_role', res.role)
                    localStorage.setItem('user_tz', res.timezone)
                    const redirectPath = sessionStorage.getItem('redirect') || '/'
                    sessionStorage.removeItem('redirect')
                    router.push(redirectPath)
            } else {
                ElMessage.error('Invalid credentials');
            }
        } else {
            ElMessage.error('Login failed, missing username and password');
            return false;
        }
    });
};

function jumpToLastPage() {
    router.push('/')
}

</script>

<template>
  <div class="container" ref="login">
    <div class="login-box">
      <h2 class="title">AlertHub</h2>
      <div class="background">
        <div class="form-container">
          <el-form
            ref="ruleFormRef"
            :model="ruleForm"
            :rules="rules"
            style="max-width: 600px"
          >
            <el-form-item label="Username" prop="userName">
              <el-input v-model="ruleForm.userName" type="text" autocomplete="off" />
            </el-form-item>

            <el-form-item label="Password" prop="password">
              <el-input v-model="ruleForm.password" type="password" autocomplete="off" />
            </el-form-item>

            <el-form-item>
              <el-button type="success" @click="submitForm(ruleFormRef)">Login</el-button>
              <el-button type="primary" @click="jumpToLastPage()">Cancel</el-button>
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  box-sizing: border-box;
}

.container {
  /*background-image: url('@/assets/images/background.jpeg');*/
  background-size: cover;
  background-position: center;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.login-box {
  display: flex;
  flex-direction: column;
  align-items: center; /* center both h1 and box */
}

.title {
  text-align: center;
  margin-bottom: 20px; /* space between title and box */
}

.background {
  background-color: rgba(248, 248, 249, 0.9);
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}

.form-container {
  width: 380px;
}
</style>

