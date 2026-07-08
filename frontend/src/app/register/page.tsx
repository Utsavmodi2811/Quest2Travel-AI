'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { authApi } from '@/lib/api';
import { companyApi } from "@/lib/api";
import { Company } from "@/types";
export default function RegisterPage() {

  const router = useRouter();

  const [form, setForm] = useState({
    employee_id: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    company_id: '',
    department: '',
    designation: '',
  });

  const [loading, setLoading] = useState(false);

  const [error, setError] = useState('');
  const [companies, setCompanies] = useState<Company[]>([]);
useEffect(() => {

  async function loadCompanies() {

    try {

      const data = await companyApi.list();

      setCompanies(data);

    } catch (err) {

      console.error(err);

    }

  }

  loadCompanies();

}, []);
  async function handleSubmit(
    e: React.FormEvent
  ) {

    e.preventDefault();

    setError('');

    setLoading(true);

    try {

      await authApi.register(form);

      router.push('/login');

    } catch (err: any) {

      setError(err.message);

    }

    setLoading(false);

  }

  return (

    <div className="min-h-screen flex items-center justify-center bg-gray-100">

      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-xl shadow-xl w-full max-w-lg"
      >

        <h1 className="text-3xl font-bold mb-6 text-center">
          Register
        </h1>

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="Employee ID"
          value={form.employee_id}
          onChange={(e)=>
            setForm({
              ...form,
              employee_id:e.target.value,
            })
          }
        />

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="First Name"
          value={form.first_name}
          onChange={(e)=>
            setForm({
              ...form,
              first_name:e.target.value,
            })
          }
        />

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="Last Name"
          value={form.last_name}
          onChange={(e)=>
            setForm({
              ...form,
              last_name:e.target.value,
            })
          }
        />

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="Email"
          value={form.email}
          onChange={(e)=>
            setForm({
              ...form,
              email:e.target.value,
            })
          }
        />

        <input
          type="password"
          className="w-full border rounded p-3 mb-3"
          placeholder="Password"
          value={form.password}
          onChange={(e)=>
            setForm({
              ...form,
              password:e.target.value,
            })
          }
        />

        <select
        className="w-full border rounded p-3 mb-3"
        value={form.company_id}
        onChange={(e) =>
            setForm({
            ...form,
            company_id: e.target.value,
            })
        }
        >

        <option value="">
            Select Company
        </option>

        {companies.map((company) => (

            <option
            key={company.company_id}
            value={company.company_id}
            >
            {company.name}
            </option>

        ))}

        </select>

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="Department"
          value={form.department}
          onChange={(e)=>
            setForm({
              ...form,
              department:e.target.value,
            })
          }
        />

        <input
          className="w-full border rounded p-3 mb-3"
          placeholder="Designation"
          value={form.designation}
          onChange={(e)=>
            setForm({
              ...form,
              designation:e.target.value,
            })
          }
        />

        {error && (

          <p className="text-red-600 mb-4">
            {error}
          </p>

        )}
        <p className="text-center mt-4 text-sm text-gray-600">
        Already have an account?{" "}
        <button
            type="button"
            onClick={() => router.push("/login")}
            className="text-blue-600 hover:underline"
        >
            Login
        </button>
        </p>
        <button
          disabled={loading}
          className="w-full bg-blue-600 text-white rounded-lg p-3"
        >

          {loading
            ? "Creating Account..."
            : "Register"}

        </button>

      </form>

    </div>

  );

}