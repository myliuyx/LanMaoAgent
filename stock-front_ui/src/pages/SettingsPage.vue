<script setup lang="ts">
import { ElCard, ElDescriptions, ElDescriptionsItem, ElTag } from 'element-plus'

const APP_VERSION = import.meta.env.APP_VERSION as string || '1.1.1'
</script>

<template>
  <div class="page-container">
    <h2 class="page-title">系统设置</h2>

    <el-card shadow="hover">
      <el-descriptions title="系统信息" :column="2" border>
        <el-descriptions-item label="环境">开发环境</el-descriptions-item>
        <el-descriptions-item label="版本">v{{ APP_VERSION }}</el-descriptions-item>
        <el-descriptions-item label="数据库状态">
          <el-tag type="success" size="small">正常</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="调度器状态">
          <el-tag type="success" size="small">运行中</el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>
